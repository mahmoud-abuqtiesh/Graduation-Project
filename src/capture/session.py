
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, List

from src.capture.pi_config import load_pi_config
from src.capture.supervisor import CaptureSupervisor

@contextmanager
def capture_session(
    camera_indices: List[int], *, startup_timeout: float = 8.0
) -> Iterator[CaptureSupervisor]:
    supervisor = CaptureSupervisor(
        camera_indices=camera_indices,
        pi_config=load_pi_config(),
    )
    try:
        supervisor.start(timeout=startup_timeout)
    except RuntimeError as exc:
        if len(camera_indices) == 1:
            raise RuntimeError(
                f"Could not open Camera {camera_indices[0]}. "
                f"Try selecting another camera or closing other apps that may be using it. "
                f"Detail: {exc}"
            ) from exc
        raise RuntimeError(
            "Could not open one or both cameras. "
            "Try closing other apps that may be using them. "
            f"Detail: {exc}"
        ) from exc

    try:
        yield supervisor
    finally:
        supervisor.stop()

def assert_capture_alive(supervisor: CaptureSupervisor) -> None:
    if not supervisor.is_alive():
        tail = supervisor.last_stderr_lines(3)
        raise RuntimeError(
            f"Capture process exited unexpectedly. Last stderr: {tail}"
        )
