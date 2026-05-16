
from __future__ import annotations

import collections
import shlex
import sys
import threading
import time
from typing import Deque, List, Optional

from src.capture._ssh import (
    SshConnectError,
    SshPopen,
    kill_remote_capture,
    ssh_popen,
)
from src.capture.frame_receiver import FrameReceiver
from src.capture.pi_config import PiConfig, load_pi_config

_initial_cleanup_lock = threading.Lock()
_initial_cleanup_done = False

def _run_initial_cleanup_once(cfg: PiConfig) -> None:
    global _initial_cleanup_done
    with _initial_cleanup_lock:
        if not _initial_cleanup_done:
            return
        _initial_cleanup_done = True
    kill_remote_capture(cfg)

class CaptureSupervisor:
    def __init__(
        self,
        camera_indices: List[int],
        pi_config: Optional[PiConfig] = None,
    ) -> None:
        if len(camera_indices) not in (1, 2):
            raise ValueError(
                f"camera_indices must have 1 or 2 entries, got {len(camera_indices)}"
            )
        self._camera_indices: List[int] = [int(i) for i in camera_indices]
        self._pi_config: PiConfig = pi_config or load_pi_config()
        self._receiver: Optional[FrameReceiver] = None
        self._proc: Optional[SshPopen] = None
        self._stderr_thread: Optional[threading.Thread] = None
        self._ready_event = threading.Event()
        self._ready_ok = False
        self._ready_reason = ""
        self._stderr_lines: Deque[str] = collections.deque(maxlen=50)
        self._stderr_lock = threading.Lock()

    @property
    def receiver(self) -> FrameReceiver:
        if self._receiver is None:
            raise RuntimeError("CaptureSupervisor not started")
        return self._receiver

    def is_alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def last_stderr_lines(self, n: int = 10) -> List[str]:
        with self._stderr_lock:
            lines = list(self._stderr_lines)
        return lines[-n:]

    def start(self, timeout: float = 8.0) -> None:
        if self._receiver is not None or self._proc is not None:
            raise RuntimeError("CaptureSupervisor already started")

        if not self._pi_config.is_usable:
            raise RuntimeError(
                "Pi config incomplete -- create a pi.json with "
                "host/user/password/install_dir. See src/capture/pi_config.py "
                "for the expected schema."
            )

        receiver = FrameReceiver(host="0.0.0.0", port=0)
        receiver.start()
        self._receiver = receiver
        port = receiver.actual_port

        _run_initial_cleanup_once(self._pi_config)

        try:
            remote_cmd = self._build_remote_cmd(port)
            self._proc = ssh_popen(self._pi_config, remote_cmd)
        except SshConnectError as exc:
            receiver.stop()
            self._receiver = None
            raise RuntimeError(str(exc)) from exc

        self._stderr_thread = threading.Thread(
            target=self._pump_stderr, daemon=True, name="capture-stderr-pump"
        )
        self._stderr_thread.start()

        if not self._ready_event.wait(timeout=timeout):
            tail = self.last_stderr_lines(5)
            self.stop()
            raise RuntimeError(
                f"capture process did not signal ready within {timeout}s. "
                f"Last stderr lines: {tail}"
            )

        if not self._ready_ok:
            reason = self._ready_reason
            self.stop()
            raise RuntimeError(reason or "capture process failed to start")

    def _build_remote_cmd(self, port: int) -> str:
        cfg = self._pi_config
        cam_args = ["--cam0", str(self._camera_indices[0])]
        if len(self._camera_indices) == 2:
            cam_args += ["--cam1", str(self._camera_indices[1])]

        remote_python = f"{cfg.install_dir}/venv/bin/python"
        parts = [
            "cd", shlex.quote(cfg.install_dir), "&&",
            "exec", shlex.quote(remote_python),
            "-m", "src.capture.frame_capture",
            *cam_args,
            "--host", shlex.quote(cfg.laptop_host),
            "--port", str(port),
        ]
        return " ".join(parts)

    def _pump_stderr(self) -> None:
        proc = self._proc
        if proc is None:
            return
        try:
            for raw in proc.stderr:
                line = raw.rstrip()
                if not line:
                    continue
                with self._stderr_lock:
                    self._stderr_lines.append(line)
                try:
                    sys.stderr.write(f"[capture] {line}\n")
                    sys.stderr.flush()
                except OSError:
                    pass
                if not self._ready_event.is_set() and line.startswith("READY="):
                    self._handle_ready(line)
        except (OSError, EOFError):
            return

    def _handle_ready(self, line: str) -> None:
        if line.startswith("READY=1"):
            self._ready_ok = True
            self._ready_event.set()
            return
        if line.startswith("READY=0"):
            self._ready_ok = False
            after = line[len("READY=0"):].strip()
            if after.startswith("reason="):
                self._ready_reason = after[len("reason="):]
            else:
                self._ready_reason = after
            self._ready_event.set()

    def stop(self, grace: float = 2.0) -> None:
        proc = self._proc
        if proc is not None:
            if proc.poll() is None:
                try:
                    proc.terminate()
                except OSError:
                    pass
                try:
                    proc.wait(timeout=grace)
                except (TimeoutError, OSError):
                    try:
                        proc.kill()
                    except OSError:
                        pass
                    try:
                        proc.wait(timeout=1.0)
                    except (TimeoutError, OSError):
                        pass
            try:
                proc.close()
            except OSError:
                pass
            self._proc = None

        if self._stderr_thread is not None:
            self._stderr_thread.join(timeout=1.0)
            self._stderr_thread = None

        kill_remote_capture(self._pi_config)

        if self._receiver is not None:
            self._receiver.stop()
            self._receiver = None
