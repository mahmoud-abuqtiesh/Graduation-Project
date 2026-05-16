from typing import Dict, Optional, Tuple

from src.face_tracking.controllers.blendshape_gesture_constants import (
    CLICK_HOLD_TRIGGER_SEC,
    CLICK_HOLD_UNFREEZE_SEC,
    PUCKER_MAX,
    PUCKER_RELEASE,
    PUCKER_TRIGGER_HIGH,
    PUCKER_TRIGGER_LOW,
    SCROLL_INTENT_DELAY_SEC,
    SCROLL_MIN_TICK_INTERVAL_SEC,
    SMIRK_RELAX_DIFF,
    SMIRK_TRIGGER_DIFF,
    TUCK_RELEASE,
    TUCK_TRIGGER_HIGH,
    TUCK_TRIGGER_LOW,
)
from src.face_tracking.signals.blendshapes import (
    compute_smirk_activations,
    pucker_value,
    tuck_value,
)
class GestureController:

    def __init__(
        self,
        cursor,
        smirk_trigger_diff: float = SMIRK_TRIGGER_DIFF,
        smirk_relax_diff: float = SMIRK_RELAX_DIFF,
        smirk_baseline_left: float = 0.0,
        smirk_baseline_right: float = 0.0,
        click_hold_unfreeze_sec: float = CLICK_HOLD_UNFREEZE_SEC,
        click_hold_trigger_sec: float = CLICK_HOLD_TRIGGER_SEC,
        pucker_release: float = PUCKER_RELEASE,
        pucker_trigger_low: float = PUCKER_TRIGGER_LOW,
        pucker_trigger_high: float = PUCKER_TRIGGER_HIGH,
        pucker_max: float = PUCKER_MAX,
        pucker_baseline: float = 0.0,
        tuck_release: float = TUCK_RELEASE,
        tuck_trigger_low: float = TUCK_TRIGGER_LOW,
        tuck_trigger_high: float = TUCK_TRIGGER_HIGH,
        tuck_baseline: float = 0.0,
        scroll_intent_delay_sec: float = SCROLL_INTENT_DELAY_SEC,
        scroll_min_tick_interval_sec: float = SCROLL_MIN_TICK_INTERVAL_SEC,
    ) -> None:
        if smirk_trigger_diff <= 0.0:
            raise ValueError("smirk_trigger_diff must be > 0")
        if smirk_relax_diff < 0.0 or smirk_relax_diff >= smirk_trigger_diff:
            raise ValueError("smirk_relax_diff must be in [0, smirk_trigger_diff)")
        if smirk_baseline_left < 0.0 or smirk_baseline_right < 0.0:
            raise ValueError("smirk baselines must be >= 0")
        if click_hold_unfreeze_sec < 0.0:
            raise ValueError("click_hold_unfreeze_sec must be >= 0")
        if click_hold_trigger_sec < 0.0:
            raise ValueError("click_hold_trigger_sec must be >= 0")
        if not (0.0 <= pucker_release < pucker_trigger_low < pucker_trigger_high <= pucker_max):
            raise ValueError(
                "pucker thresholds must satisfy: "
                "0 <= release < trigger_low < trigger_high <= max"
            )
        if pucker_baseline < 0.0:
            raise ValueError("pucker_baseline must be >= 0")
        if not (0.0 <= tuck_release < tuck_trigger_low < tuck_trigger_high):
            raise ValueError(
                "tuck thresholds must satisfy: 0 <= release < trigger_low < trigger_high"
            )
        if tuck_baseline < 0.0:
            raise ValueError("tuck_baseline must be >= 0")
        if scroll_intent_delay_sec < 0.0:
            raise ValueError("scroll_intent_delay_sec must be >= 0")
        if scroll_min_tick_interval_sec < 0.0:
            raise ValueError("scroll_min_tick_interval_sec must be >= 0")

        self.cursor = cursor
        minx, miny, maxx, maxy = self.cursor.get_virtual_bounds()
        self.minx = minx
        self.miny = miny
        self.maxx = maxx
        self.maxy = maxy

        self.smirk_trigger_diff = float(smirk_trigger_diff)
        self.smirk_relax_diff = float(smirk_relax_diff)
        self.smirk_baseline_left = float(smirk_baseline_left)
        self.smirk_baseline_right = float(smirk_baseline_right)
        self.click_hold_unfreeze_sec = float(click_hold_unfreeze_sec)
        self.click_hold_trigger_sec = float(click_hold_trigger_sec)
        self.pucker_release = float(pucker_release)
        self.pucker_trigger_low = float(pucker_trigger_low)
        self.pucker_trigger_high = float(pucker_trigger_high)
        self.pucker_max = float(pucker_max)
        self.pucker_baseline = float(pucker_baseline)
        self.tuck_release = float(tuck_release)
        self.tuck_trigger_low = float(tuck_trigger_low)
        self.tuck_trigger_high = float(tuck_trigger_high)
        self.tuck_baseline = float(tuck_baseline)
        self.scroll_intent_delay_sec = float(scroll_intent_delay_sec)
        self.scroll_min_tick_interval_sec = float(scroll_min_tick_interval_sec)

        self.click_enabled = True
        self.scroll_enabled = True

        self._click_armed: bool = True
        self._held_button: Optional[str] = None
        self._held_started_at: float = 0.0
        self._last_click_side: Optional[str] = None
        self._last_click_consumed: bool = False
        self._pucker_hold_intent_started_at: Optional[float] = None
        self._tuck_hold_intent_started_at: Optional[float] = None

        self._smirk_scroll_intent_started_at: Optional[float] = None
        self._scroll_last_tick_at: float = 0.0
        self._scroll_accumulator: float = 0.0
        self.active_scroll_gesture: Optional[str] = None

    def _adjusted_smirk(self, blendshapes: Dict[str, float]) -> Tuple[float, float]:
        raw_left, raw_right = compute_smirk_activations(blendshapes)
        adj_left = raw_left - self.smirk_baseline_left
        adj_right = raw_right - self.smirk_baseline_right
        if adj_left < 0.0:
            adj_left = 0.0
        if adj_right < 0.0:
            adj_right = 0.0
        return adj_left, adj_right

    def _adjusted_pucker(self, blendshapes: Dict[str, float]) -> float:
        raw = pucker_value(blendshapes)
        v = raw - self.pucker_baseline
        return v if v > 0.0 else 0.0

    def _adjusted_tuck(self, blendshapes: Dict[str, float]) -> float:
        raw = tuck_value(blendshapes)
        v = raw - self.tuck_baseline
        return v if v > 0.0 else 0.0

    def _press_held_button(self, side: str, now: float) -> None:
        if side == "left":
            self.cursor.left_down()
        elif side == "right":
            self.cursor.right_down()
        else:
            return
        self._held_button = side
        self._held_started_at = now
        self._last_click_side = side
        self._last_click_consumed = False

    def _release_held_button(self) -> None:
        if self._held_button == "left":
            self.cursor.left_up()
        elif self._held_button == "right":
            self.cursor.right_up()
        self._held_button = None
        self._held_started_at = 0.0

    def _handle_lip_click_or_hold(self, pucker: float, tuck: float, now: float) -> None:
        pucker_active = pucker >= self.pucker_release
        tuck_active = tuck >= self.tuck_release
        pucker_trigger = pucker >= self.pucker_trigger_high
        tuck_trigger = tuck >= self.tuck_trigger_high

        if self._held_button is None and not self._click_armed:
            if not pucker_active and not tuck_active:
                self._click_armed = True
                self._pucker_hold_intent_started_at = None
                self._tuck_hold_intent_started_at = None
            return

        if self._held_button is not None:
            if self._held_button == "left":
                if not pucker_active:
                    self._release_held_button()
                    self._click_armed = True
                    return
                if tuck_trigger:
                    self._release_held_button()
                    self._press_held_button("right", now)
            else:
                if not tuck_active:
                    self._release_held_button()
                    self._click_armed = True
                    return
                if pucker_trigger:
                    self._release_held_button()
                    self._press_held_button("left", now)
            return

        if pucker_trigger and self._click_armed and self._pucker_hold_intent_started_at is None:
            self.cursor.left_click()
            self._pucker_hold_intent_started_at = now
            self._click_armed = False

        if self._pucker_hold_intent_started_at is not None:
            if not pucker_trigger:
                self._pucker_hold_intent_started_at = None
            elif (now - self._pucker_hold_intent_started_at) >= self.click_hold_trigger_sec:
                self._press_held_button("left", now)
                self._pucker_hold_intent_started_at = None
            if self._pucker_hold_intent_started_at is not None:
                return

        if tuck_trigger and self._click_armed and self._tuck_hold_intent_started_at is None:
            self.cursor.right_click()
            self._tuck_hold_intent_started_at = now
            self._click_armed = False

        if self._tuck_hold_intent_started_at is not None:
            if not tuck_trigger:
                self._tuck_hold_intent_started_at = None
            elif (now - self._tuck_hold_intent_started_at) >= self.click_hold_trigger_sec:
                self._press_held_button("right", now)
                self._tuck_hold_intent_started_at = None
            if self._tuck_hold_intent_started_at is not None:
                return

    def _emit_scroll_tick(self, direction: str, speed: float, now: float) -> None:
        if (now - self._scroll_last_tick_at) < self.scroll_min_tick_interval_sec:
            return
        if self._scroll_last_tick_at == 0.0:
            elapsed = self.scroll_min_tick_interval_sec
        else:
            elapsed = now - self._scroll_last_tick_at
        self._scroll_last_tick_at = now

        clamped_speed = speed
        speed_limit = getattr(self.cursor, "scroll_units_per_sec", None)
        if speed_limit is not None:
            try:
                limit_value = float(speed_limit)
            except (TypeError, ValueError):
                limit_value = None
            if limit_value is not None and limit_value > 0.0:
                clamped_speed = limit_value

        units = clamped_speed * elapsed
        if direction != "up":
            units = -units
        self._scroll_accumulator += units

        if self._scroll_accumulator >= 1.0 or self._scroll_accumulator <= -1.0:
            delta = int(self._scroll_accumulator)
            self._scroll_accumulator -= delta
            step = 1 if delta > 0 else -1
            for _ in range(abs(delta)):
                self.cursor.scroll(step)

    def _handle_smirk_scroll(self, smirk_diff: float, now: float) -> None:
        abs_diff = abs(smirk_diff)

        if abs_diff <= self.smirk_relax_diff:
            self._smirk_scroll_intent_started_at = None
            if self.active_scroll_gesture in ("scroll_up", "scroll_down"):
                self.active_scroll_gesture = None
            self._scroll_accumulator = 0.0
            self._scroll_last_tick_at = 0.0
            return

        if self._smirk_scroll_intent_started_at is None:
            self._smirk_scroll_intent_started_at = now
            self._scroll_last_tick_at = 0.0
            return
        if (now - self._smirk_scroll_intent_started_at) < self.scroll_intent_delay_sec:
            return

        if smirk_diff > 0:
            direction = "up"
            self.active_scroll_gesture = "scroll_up"
        else:
            direction = "down"
            self.active_scroll_gesture = "scroll_down"

        speed_limit = getattr(self.cursor, "scroll_units_per_sec", None)
        try:
            speed = float(speed_limit)
        except (TypeError, ValueError):
            return
        self._emit_scroll_tick(direction, speed, now)

    def release_all(self) -> None:
        self._release_held_button()
        self._click_armed = True
        self._last_click_side = None
        self._last_click_consumed = False
        self._pucker_hold_intent_started_at = None
        self._tuck_hold_intent_started_at = None
        self._smirk_scroll_intent_started_at = None
        self._scroll_last_tick_at = 0.0
        self._scroll_accumulator = 0.0
        self.active_scroll_gesture = None

    def handle_face_analysis(self, face_analysis, now: float) -> None:
        blendshapes = face_analysis.blendshapes or {}

        pucker = self._adjusted_pucker(blendshapes)
        tuck = self._adjusted_tuck(blendshapes)
        cursor_frozen = (
            self._held_button is not None
            and (now - self._held_started_at) < self.click_hold_unfreeze_sec
        )

        if face_analysis.screen_position is not None and not cursor_frozen:
            raw_tx, raw_ty = face_analysis.screen_position
            target_x = max(self.minx, min(self.maxx, raw_tx + self.minx))
            target_y = max(self.miny, min(self.maxy, raw_ty + self.miny))
            self.cursor.step_towards(target_x, target_y)

        if self.click_enabled:
            self._handle_lip_click_or_hold(pucker, tuck, now)
        elif self._held_button is not None:
            self._release_held_button()
            self._click_armed = True

        if self._last_click_side is not None and self._last_click_consumed:
            self._last_click_side = None
        elif self._last_click_side is not None:
            self._last_click_consumed = True

        if self.scroll_enabled:
            adj_left, adj_right = self._adjusted_smirk(blendshapes)
            self._handle_smirk_scroll(adj_left - adj_right, now)
        else:
            self._smirk_scroll_intent_started_at = None
            self.active_scroll_gesture = None

    def shutdown(self) -> None:
        self.release_all()
