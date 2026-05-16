
import time
from typing import Callable, Optional

class IdleController:
    def __init__(
        self,
        idle_after_frames: int = 30,
        idle_sleep_s: float = 1.0,
    ) -> None:
        self.idle_after_frames = max(1, int(idle_after_frames))
        self.idle_sleep_s = max(0.0, float(idle_sleep_s))
        self._streak = 0
        self._is_idle = False
        self._on_change: Optional[Callable[[bool], None]] = None

    @property
    def is_idle(self) -> bool:
        return self._is_idle

    @property
    def streak_frames(self) -> int:
        return self._streak

    def observe(self, face_detected: bool) -> bool:
        if face_detected:
            self._streak = 0
            if self._is_idle:
                self._is_idle = False
                self._fire_change(False)
                return True
            return False
        self._streak += 1
        if not self._is_idle and self._streak >= self.idle_after_frames:
            self._is_idle = True
            self._fire_change(True)
            return True
        return False

    def maybe_sleep(self) -> None:
        if self._is_idle and self.idle_sleep_s > 0:
            time.sleep(self.idle_sleep_s)

    def set_on_change(self, callback: Optional[Callable[[bool], None]]) -> None:
        self._on_change = callback

    def _fire_change(self, is_idle: bool) -> None:
        if self._on_change is None:
            return
        try:
            self._on_change(is_idle)
        except Exception:
            pass

def apply_idle_settings(idle: Optional[IdleController], settings: dict) -> None:
    if idle is None or not settings:
        return
    if "idle_after_frames" in settings:
        try:
            idle.idle_after_frames = max(1, int(settings["idle_after_frames"]))
        except (TypeError, ValueError) as exc:
            print(f"warning: bad idle_after_frames, ignored: {exc}")
    if "idle_sleep_s" in settings:
        try:
            idle.idle_sleep_s = max(0.0, float(settings["idle_sleep_s"]))
        except (TypeError, ValueError) as exc:
            print(f"warning: bad idle_sleep_s, ignored: {exc}")
