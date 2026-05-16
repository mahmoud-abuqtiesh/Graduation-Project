
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.core.devices.camera_manager import CameraManager

KEY_LEFT_CAMERA_ID = "left_camera_id"
KEY_RIGHT_CAMERA_ID = "right_camera_id"
KEY_LEFT_CAMERA_STABLE_ID = "left_camera_stable_id"
KEY_RIGHT_CAMERA_STABLE_ID = "right_camera_stable_id"
KEY_CAMERA_STABLE_ID = "camera_stable_id"
KEY_CAMERA_ID = "camera_id"

@dataclass
class CameraMatch:

    ok: bool
    resolved_indices: List[int]
    reason: str = ""

def _coerce_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

def get_calibration_stable_ids(calibration: Optional[Dict]) -> Dict[str, Optional[str]]:
    if not calibration:
        return {}
    result: Dict[str, Optional[str]] = {}
    if KEY_LEFT_CAMERA_STABLE_ID in calibration:
        result["left"] = calibration.get(KEY_LEFT_CAMERA_STABLE_ID)
    if KEY_RIGHT_CAMERA_STABLE_ID in calibration:
        result["right"] = calibration.get(KEY_RIGHT_CAMERA_STABLE_ID)
    if KEY_CAMERA_STABLE_ID in calibration:
        result["camera"] = calibration.get(KEY_CAMERA_STABLE_ID)
    return result

def match_stereo_cameras(
    stereo_calibration: Dict,
    selected_cameras: List[int],
    camera_manager: Optional[CameraManager] = None,
) -> CameraMatch:
    if len(selected_cameras) < 2:
        return CameraMatch(ok=False, resolved_indices=[], reason="Two cameras are required.")

    stored_left_idx = _coerce_int(stereo_calibration.get(KEY_LEFT_CAMERA_ID))
    stored_right_idx = _coerce_int(stereo_calibration.get(KEY_RIGHT_CAMERA_ID))
    stored_left_sid = stereo_calibration.get(KEY_LEFT_CAMERA_STABLE_ID)
    stored_right_sid = stereo_calibration.get(KEY_RIGHT_CAMERA_STABLE_ID)

    selected_left, selected_right = selected_cameras[0], selected_cameras[1]
    selected_left_sid = _resolve_sid(selected_left, camera_manager)
    selected_right_sid = _resolve_sid(selected_right, camera_manager)

    if stored_left_sid and stored_right_sid:
        if stored_left_sid == stored_right_sid:
            pass
        else:
            available = [
                (selected_left_sid, selected_left),
                (selected_right_sid, selected_right),
            ]
            resolved_left = next(
                (idx for sid, idx in available if sid == stored_left_sid), None
            )
            resolved_right = next(
                (idx for sid, idx in available
                 if sid == stored_right_sid and idx != resolved_left),
                None,
            )
            if resolved_left is not None and resolved_right is not None:
                return CameraMatch(
                    ok=True,
                    resolved_indices=[resolved_left, resolved_right],
                )
            missing = []
            if resolved_left is None:
                missing.append("left")
            if resolved_right is None:
                missing.append("right")
            return CameraMatch(
                ok=False,
                resolved_indices=[],
                reason=(
                    f"Calibrated {' and '.join(missing)} camera not detected. "
                    "Reconnect the camera you used for calibration, or recalibrate."
                ),
            )

    if stored_left_idx == selected_left and stored_right_idx == selected_right:
        return CameraMatch(ok=True, resolved_indices=[selected_left, selected_right])

    if stored_left_idx == selected_right and stored_right_idx == selected_left:
        return CameraMatch(
            ok=True,
            resolved_indices=[selected_left, selected_right],
        )

    return CameraMatch(
        ok=False,
        resolved_indices=[],
        reason=(
            "Stereo calibration was created for different cameras. Please recalibrate, "
            "or use the Swap Left/Right button if the cables are crossed."
        ),
    )

def match_single_camera(
    calibration: Dict,
    selected_camera: int,
    *,
    label: str = "calibration",
    camera_manager: Optional[CameraManager] = None,
) -> CameraMatch:
    stored_sid = calibration.get(KEY_CAMERA_STABLE_ID) if calibration else None
    if not stored_sid:
        return CameraMatch(ok=True, resolved_indices=[selected_camera])

    selected_sid = _resolve_sid(selected_camera, camera_manager)
    if selected_sid and selected_sid == stored_sid:
        return CameraMatch(ok=True, resolved_indices=[selected_camera])

    if camera_manager is not None:
        remap = camera_manager.index_for_stable_id(stored_sid)
        if remap is not None:
            return CameraMatch(ok=True, resolved_indices=[remap])

    return CameraMatch(
        ok=False,
        resolved_indices=[],
        reason=(
            f"This {label} was created on a different camera. "
            "Please recalibrate or reconnect the original camera."
        ),
    )

def warn_if_single_camera_mismatch(
    calibration: Optional[Dict],
    selected_camera: int,
    *,
    label: str = "calibration",
    camera_manager: Optional[CameraManager] = None,
) -> Optional[str]:
    if not calibration:
        return None
    stored_sid = calibration.get(KEY_CAMERA_STABLE_ID)
    if not stored_sid:
        return None
    if camera_manager is None:
        return None
    selected_sid = _resolve_sid(selected_camera, camera_manager)
    if not selected_sid or selected_sid == stored_sid:
        return None
    return (
        f"Note: this {label} was created on a different physical camera. "
        "It should still work but accuracy may be reduced; recalibrate "
        "if you notice issues."
    )

def annotate_stereo_calibration(
    calibration: Dict,
    left_index: int,
    right_index: int,
    camera_manager: Optional[CameraManager] = None,
) -> Dict:
    left_sid = _resolve_sid(left_index, camera_manager)
    right_sid = _resolve_sid(right_index, camera_manager)
    if left_sid:
        calibration[KEY_LEFT_CAMERA_STABLE_ID] = left_sid
    if right_sid:
        calibration[KEY_RIGHT_CAMERA_STABLE_ID] = right_sid
    return calibration

def annotate_single_camera_calibration(
    calibration: Dict,
    camera_index: int,
    camera_manager: Optional[CameraManager] = None,
) -> Dict:
    sid = _resolve_sid(camera_index, camera_manager)
    calibration.setdefault(KEY_CAMERA_ID, int(camera_index))
    if sid:
        calibration[KEY_CAMERA_STABLE_ID] = sid
    return calibration

def _resolve_sid(index: int, camera_manager: Optional[CameraManager]) -> Optional[str]:
    if camera_manager is None:
        return None
    return camera_manager.stable_id_for_index(index)
