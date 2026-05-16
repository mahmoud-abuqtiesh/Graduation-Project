from pathlib import Path

from platformdirs import user_data_dir

from src.capture.pi_config import load_pi_config
from src.core.devices.camera_manager import CameraManager
from src.core.modes.registry import ModeRegistry
from src.core.profiles.profile_manager import ProfileManager
from src.ui.main_window import MainWindow

def _register_modes(registry: ModeRegistry) -> None:
    from src.core.modes.one_camera_head_pose import OneCameraHeadPoseMode
    from src.core.modes.two_camera_head_pose import TwoCameraHeadPoseMode
    from src.core.modes.eye_gaze import EyeGazeMode
    from src.core.modes.eye_gaze_bubble import EyeGazeBubbleMode
    from src.core.modes.bubble_lock import HybridBubbleLockMode

    registry.register(OneCameraHeadPoseMode)
    registry.register(TwoCameraHeadPoseMode)
    registry.register(EyeGazeMode)
    registry.register(EyeGazeBubbleMode)
    registry.register(HybridBubbleLockMode)

def initialize_app() -> MainWindow:
    data_dir = Path(user_data_dir("EyeCursor", "EyeCursorTeam"))
    data_dir.mkdir(parents=True, exist_ok=True)

    profile_manager = ProfileManager(data_dir)
    mode_registry = ModeRegistry()
    _register_modes(mode_registry)
    camera_manager = CameraManager(pi_config=load_pi_config())

    window = MainWindow(
        profile_manager=profile_manager,
        mode_registry=mode_registry,
        camera_manager=camera_manager,
    )
    return window
