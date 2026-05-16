from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

class TrackingMode(ABC):
    id: str = ""
    display_name: str = ""
    description: str = ""
    required_camera_count: int = 1
    requires_head_pose_calibration: bool = False
    requires_facial_gesture_calibration: bool = False
    requires_stereo_calibration: bool = False
    requires_gaze_calibration: bool = False

    @abstractmethod
    def validate_requirements(
        self,
        profile_calibrations: Dict[str, Optional[dict]],
        selected_cameras: List[int],
        camera_manager: Optional[Any] = None,
    ) -> Tuple[bool, str]:
        ...

    @abstractmethod
    def start(
        self,
        profile_calibrations: Dict[str, Optional[dict]],
        selected_cameras: List[int],
        cursor,
        settings: Optional[dict] = None,
    ) -> None:
        ...

    @abstractmethod
    def stop(self) -> None:
        ...

    @abstractmethod
    def pause(self) -> None:
        ...

    @abstractmethod
    def resume(self) -> None:
        ...

    def update_settings(self, settings: Dict) -> None:
        return
