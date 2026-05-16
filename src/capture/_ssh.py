
from __future__ import annotations

import platform
import subprocess
import threading
import time
from typing import IO, Optional, Tuple

try:
    import paramiko
except ImportError as exc:
    raise ImportError(
        "paramiko is required for Pi capture. Install it with:\n"
        "  pip install paramiko\n"
        "Or re-run setup_windows.bat / setup_linux.sh to refresh the venv."
    ) from exc

from src.capture.pi_config import PiConfig

_CONNECT_TIMEOUT_S = 5.0

_KEEPALIVE_S = 3.0

class SshConnectError(RuntimeError):
    pass

def _connect(cfg: PiConfig, *, timeout: float = _CONNECT_TIMEOUT_S) -> paramiko.SSHClient:
    if not cfg.is_usable:
        raise SshConnectError(
            "Pi config incomplete -- need host/user/install_dir + password."
        )
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=cfg.host,
            username=cfg.user,
            password=cfg.password,
            timeout=timeout,
            banner_timeout=timeout,
            auth_timeout=timeout,
            allow_agent=False,
            look_for_keys=False,
        )
    except (paramiko.AuthenticationException,
            paramiko.SSHException,
            OSError,
            EOFError) as exc:
        try:
            client.close()
        except Exception:
            pass
        raise SshConnectError(f"SSH connect to {cfg.user}@{cfg.host} failed: {exc}") from exc
    transport = client.get_transport()
    if transport is not None:
        transport.set_keepalive(int(_KEEPALIVE_S))
    return client

def ssh_run(
    cfg: PiConfig,
    command: str,
    *,
    timeout: float = 12.0,
) -> Tuple[str, str, int]:
    client = _connect(cfg)
    try:
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        rc = stdout.channel.recv_exit_status()
        return out, err, rc
    finally:
        client.close()

class SshPopen:

    def __init__(self, client: paramiko.SSHClient, channel: paramiko.Channel) -> None:
        self._client = client
        self._channel = channel
        self.returncode: Optional[int] = None
        self.stderr: IO[str] = _ChannelTextStream(channel.makefile_stderr("rb"))
        self.stdout: IO[str] = _ChannelTextStream(channel.makefile("rb"))

    def poll(self) -> Optional[int]:
        if self.returncode is not None:
            return self.returncode
        if self._channel.exit_status_ready():
            self.returncode = self._channel.recv_exit_status()
            return self.returncode
        if self._channel.closed:
            self.returncode = -1
            return self.returncode
        return None

    def wait(self, timeout: Optional[float] = None) -> int:
        deadline = None if timeout is None else (time.monotonic() + timeout)
        while True:
            rc = self.poll()
            if rc is not None:
                return rc
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError("SshPopen.wait timed out")
            time.sleep(0.05)

    def terminate(self) -> None:
        try:
            self._channel.close()
        except Exception:
            pass

    def kill(self) -> None:
        self.terminate()

    def close(self) -> None:
        try:
            self._channel.close()
        except Exception:
            pass
        try:
            self._client.close()
        except Exception:
            pass

class _ChannelTextStream:

    def __init__(self, byte_stream) -> None:
        self._stream = byte_stream

    def __iter__(self):
        return self

    def __next__(self) -> str:
        line = self._stream.readline()
        if not line:
            raise StopIteration
        if isinstance(line, bytes):
            return line.decode("utf-8", errors="replace")
        return line

    def readline(self) -> str:
        line = self._stream.readline()
        if isinstance(line, bytes):
            return line.decode("utf-8", errors="replace")
        return line

    def close(self) -> None:
        try:
            self._stream.close()
        except Exception:
            pass

def ssh_popen(cfg: PiConfig, command: str) -> SshPopen:
    client = _connect(cfg)
    transport = client.get_transport()
    if transport is None:
        client.close()
        raise SshConnectError("SSH transport unavailable after connect")
    try:
        channel = transport.open_session(timeout=_CONNECT_TIMEOUT_S)
        channel.exec_command(command)
    except (paramiko.SSHException, OSError) as exc:
        client.close()
        raise SshConnectError(f"failed to start remote command: {exc}") from exc
    return SshPopen(client, channel)

def scp_put(cfg: PiConfig, local_path: str, remote_path: str) -> None:
    client = _connect(cfg)
    try:
        sftp = client.open_sftp()
        try:
            sftp.put(local_path, remote_path)
        finally:
            sftp.close()
    finally:
        client.close()

def pi_reachable(host: str, *, timeout_s: float = 1.0) -> bool:
    if not host:
        return False
    if platform.system() == "Windows":
        argv = ["ping", "-n", "1", "-w", str(int(timeout_s * 1000)), host]
    elif platform.system() == "Darwin":
        argv = ["ping", "-c", "1", "-W", str(int(timeout_s * 1000)), host]
    else:
        argv = ["ping", "-c", "1", "-W", str(int(timeout_s)), host]
    try:
        result = subprocess.run(
            argv,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout_s + 1,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False

def kill_remote_capture(cfg: PiConfig, *, timeout_s: float = 4.0) -> None:
    try:
        ssh_run(
            cfg,
            "pkill -f 'src.capture.frame_capture' || true",
            timeout=timeout_s,
        )
    except (SshConnectError, OSError):
        pass

__all__ = [
    "SshConnectError",
    "SshPopen",
    "ssh_run",
    "ssh_popen",
    "scp_put",
    "pi_reachable",
    "kill_remote_capture",
]
