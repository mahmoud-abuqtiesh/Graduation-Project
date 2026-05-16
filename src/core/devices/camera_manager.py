
from __future__ import annotations

import json
from typing import Dict, FrozenSet, List, Optional, Tuple

import numpy as np

from src.capture._ssh import (
    SshConnectError,
    pi_reachable,
    ssh_run,
)
from src.capture.frame_capture import (
    SINGLE_CAM_ID,
    STEREO_LEFT_CAM_ID,
    STEREO_RIGHT_CAM_ID,
)
from src.capture.pi_config import PiConfig, load_pi_config
from src.capture.supervisor import CaptureSupervisor
from src.core.devices.camera_model import CameraInfo
from src.core.devices.stable_camera_id import build_pi_stable_id

_PROBE_TIMEOUT_S = 12.0
_PING_TIMEOUT_S = 1.0

class _OpenCam:

    def __init__(self, supervisor: CaptureSupervisor) -> None:
        self.supervisor = supervisor
        self.last_ts: float = 0.0

class _OpenStereo:

    def __init__(self, supervisor: CaptureSupervisor, left_index: int, right_index: int) -> None:
        self.supervisor = supervisor
        self.left_index = left_index
        self.right_index = right_index
        self.last_ts_left: float = 0.0
        self.last_ts_right: float = 0.0

def _stereo_key(left_index: int, right_index: int) -> FrozenSet[int]:
    return frozenset({left_index, right_index})

class CameraManager:
    def __init__(self, pi_config: Optional[PiConfig] = None) -> None:
        self._pi_config: PiConfig = pi_config or load_pi_config()
        self._open_cameras: Dict[int, _OpenCam] = {}
        self._open_stereo: Dict[FrozenSet[int], _OpenStereo] = {}
        self._last_scan: List[CameraInfo] = []
        self._last_error: Optional[str] = None

    @property
    def pi_config(self) -> PiConfig:
        return self._pi_config

    def last_error(self) -> Optional[str]:
        return self._last_error

    def discover_cameras(self) -> List[CameraInfo]:
        self._last_error = None
        cfg = self._pi_config

        if not cfg.is_usable:
            self._last_error = (
                "Raspberry Pi config is incomplete. Edit pi.json with "
                "host/user and either password or key_path."
            )
            self._last_scan = []
            return []

        if not self._pi_reachable():
            self._last_error = (
                f"Raspberry Pi not reachable at {cfg.host}. "
                "Check the Ethernet cable and that the Pi is powered on."
            )
            self._last_scan = []
            return []

        probe_cmd = (
            f"{cfg.install_dir}/venv/bin/python "
            f"{cfg.install_dir}/src/capture/probe.py"
        )
        try:
            stdout, stderr, rc = ssh_run(cfg, probe_cmd, timeout=_PROBE_TIMEOUT_S)
        except SshConnectError as exc:
            self._last_error = f"Could not SSH to the Pi: {exc}"
            self._last_scan = []
            return []
        except OSError as exc:
            self._last_error = f"Could not SSH to the Pi: {exc}"
            self._last_scan = []
            return []

        if rc != 0:
            self._last_error = (
                f"Pi probe failed (exit {rc}). "
                f"stderr: {stderr.strip()[:200]}"
            )
            self._last_scan = []
            return []

        try:
            entries = json.loads(stdout)
        except json.JSONDecodeError as exc:
            self._last_error = (
                f"Pi probe returned non-JSON output: {exc}. "
                f"stdout: {stdout[:200]!r}"
            )
            self._last_scan = []
            return []

        cameras: List[CameraInfo] = []
        for entry in entries:
            try:
                idx = int(entry["index"])
                width = int(entry.get("width") or 0)
                height = int(entry.get("height") or 0)
            except (KeyError, TypeError, ValueError):
                continue
            stable = build_pi_stable_id(entry)
            cameras.append(
                CameraInfo(
                    index=idx,
                    width=width,
                    height=height,
                    stable_id=stable,
                )
            )

        self._last_scan = cameras
        return cameras

    def _pi_reachable(self) -> bool:
        return pi_reachable(self._pi_config.host, timeout_s=_PING_TIMEOUT_S)

    def open_camera(self, index: int) -> CaptureSupervisor:
        existing = self._open_cameras.get(index)
        if existing is not None and existing.supervisor.is_alive():
            return existing.supervisor
        if existing is not None:
            self._stop_silently(existing)
            self._open_cameras.pop(index, None)

        supervisor = CaptureSupervisor(
            camera_indices=[index],
            pi_config=self._pi_config,
        )
        try:
            supervisor.start()
        except RuntimeError as exc:
            raise RuntimeError(
                f"Could not open Camera {index} on the Pi. "
                f"Try selecting another camera or checking that the cable is plugged in. "
                f"Detail: {exc}"
            ) from exc

        self._open_cameras[index] = _OpenCam(supervisor)
        return supervisor

    def get_frame(self, index: int) -> Optional[np.ndarray]:
        entry = self._open_cameras.get(index)
        if entry is None or not entry.supervisor.is_alive():
            return None
        latest = entry.supervisor.receiver.get_latest_bgr(
            cam_id=SINGLE_CAM_ID,
            since=entry.last_ts,
            timeout=0.015,
        )
        if latest is None:
            return None
        frame, ts = latest
        entry.last_ts = ts
        return frame

    def release_camera(self, index: int) -> None:
        entry = self._open_cameras.pop(index, None)
        if entry is not None:
            self._stop_silently(entry)

    def open_stereo_pair(self, left_index: int, right_index: int) -> CaptureSupervisor:
        if left_index == right_index:
            raise ValueError("open_stereo_pair requires two distinct camera indices")

        key = _stereo_key(left_index, right_index)
        existing = self._open_stereo.get(key)
        if existing is not None and existing.supervisor.is_alive():
            return existing.supervisor
        if existing is not None:
            self._stop_silently(existing)
            self._open_stereo.pop(key, None)

        supervisor = CaptureSupervisor(
            camera_indices=[left_index, right_index],
            pi_config=self._pi_config,
        )
        try:
            supervisor.start()
        except RuntimeError as exc:
            raise RuntimeError(
                f"Could not open stereo pair (cameras {left_index} + {right_index}) on the Pi. "
                f"Try selecting different cameras or checking that the cable is plugged in. "
                f"Detail: {exc}"
            ) from exc

        entry = _OpenStereo(supervisor, left_index, right_index)
        self._open_stereo[key] = entry
        return supervisor

    def get_stereo_frames(
        self,
        left_index: int,
        right_index: int,
        timeout: float = 0.05,
        max_skew: float = 0.05,
    ) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        key = _stereo_key(left_index, right_index)
        entry = self._open_stereo.get(key)
        if entry is None or not entry.supervisor.is_alive():
            return None

        pair = entry.supervisor.receiver.get_latest_pair(
            cam_id_left=STEREO_LEFT_CAM_ID,
            cam_id_right=STEREO_RIGHT_CAM_ID,
            timeout=timeout,
            max_skew=max_skew,
            since_left=entry.last_ts_left,
            since_right=entry.last_ts_right,
        )
        if pair is None:
            return None

        left_frame, right_frame, left_ts, right_ts = pair
        entry.last_ts_left = left_ts
        entry.last_ts_right = right_ts
        return left_frame, right_frame

    def release_stereo_pair(self, left_index: int, right_index: int) -> None:
        entry = self._open_stereo.pop(_stereo_key(left_index, right_index), None)
        if entry is not None:
            self._stop_silently(entry)

    def release_all(self) -> None:
        for entry in list(self._open_cameras.values()):
            self._stop_silently(entry)
        self._open_cameras.clear()
        for stereo in list(self._open_stereo.values()):
            self._stop_silently(stereo)
        self._open_stereo.clear()

    def is_open(self, index: int) -> bool:
        entry = self._open_cameras.get(index)
        return entry is not None and entry.supervisor.is_alive()

    @staticmethod
    def _stop_silently(entry) -> None:
        try:
            entry.supervisor.stop()
        except Exception:
            pass

    def stable_id_for_index(self, index: int) -> Optional[str]:
        if not self._last_scan:
            self.discover_cameras()
        for cam in self._last_scan:
            if cam.index == index:
                return cam.stable_id
        return None

    def index_for_stable_id(self, stable_id: Optional[str]) -> Optional[int]:
        if not stable_id:
            return None
        cameras = self._last_scan or self.discover_cameras()
        for cam in cameras:
            if cam.stable_id == stable_id:
                return cam.index
        return None
