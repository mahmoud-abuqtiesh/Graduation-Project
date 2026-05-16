from typing import List, Optional, Type

from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget
from PySide6.QtCore import Signal

from src.core.modes.base import TrackingMode
from src.ui.components.mode_card import ModeCard

class ModesPage(QWidget):
    mode_selected = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Tracking Modes")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        subtitle = QLabel("Select a tracking mode to use with EyeCursor.")
        subtitle.setStyleSheet("color: #636e72; font-size: 13px;")
        layout.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._cards_widget = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_widget)
        self._cards_layout.setSpacing(12)
        self._cards_layout.addStretch()
        scroll.setWidget(self._cards_widget)
        layout.addWidget(scroll)

        self._cards: dict[str, ModeCard] = {}

    def populate_modes(
        self,
        mode_classes: List[Type[TrackingMode]],
        active_mode_id: Optional[str],
        calibration_statuses: Optional[dict] = None,
        camera_selection: Optional[dict] = None,
    ) -> None:
        for card in self._cards.values():
            self._cards_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()

        for mode_cls in mode_classes:
            calibration_requirements = self._build_calibration_requirements(
                mode_cls, calibration_statuses, camera_selection
            )
            is_ready = all(flag for _, flag in calibration_requirements)
            cal_label = "Ready" if is_ready else "Not Ready"

            card = ModeCard(
                mode_id=mode_cls.id,
                display_name=mode_cls.display_name,
                description=mode_cls.description,
                calibration_requirements=calibration_requirements,
                required_cameras=mode_cls.required_camera_count,
                calibration_label=cal_label,
                is_ready=is_ready,
                is_active=(mode_cls.id == active_mode_id),
            )
            card.selected.connect(self._on_mode_selected)
            insert_index = self._cards_layout.count() - 1
            self._cards_layout.insertWidget(insert_index, card)
            self._cards[mode_cls.id] = card

    def _on_mode_selected(self, mode_id: str) -> None:
        for mid, card in self._cards.items():
            card.set_active(mid == mode_id)
        self.mode_selected.emit(mode_id)

    def set_active_mode(self, mode_id: str) -> None:
        for mid, card in self._cards.items():
            card.set_active(mid == mode_id)

    @staticmethod
    def _build_calibration_requirements(
        mode_cls: Type[TrackingMode],
        calibration_statuses: Optional[dict],
        camera_selection: Optional[dict],
    ) -> list[tuple[str, bool]]:
        statuses = calibration_statuses or {}
        cameras = camera_selection or {}
        requirements: list[tuple[str, bool]] = []

        cam_count = int(getattr(mode_cls, "required_camera_count", 0) or 0)
        if cam_count > 0:
            if cam_count == 1:
                ok = bool(cameras.get("one_camera") is not None or cameras.get("eye_gaze") is not None)
                requirements.append(("1 Camera", ok))
            elif cam_count == 2:
                ok = bool(
                    cameras.get("two_camera_left") is not None
                    and cameras.get("two_camera_right") is not None
                )
                requirements.append(("2 Cameras", ok))
            else:
                requirements.append((f"{cam_count} Cameras", False))

        if getattr(mode_cls, "requires_head_pose_calibration", False):
            if mode_cls.id in ("two_camera_head_pose", "hybrid_bubble_lock"):
                ok = bool(
                    statuses.get("two_camera_head_pose")
                    or statuses.get("one_camera_head_pose")
                )
                requirements.append(("Head pose", ok))
            else:
                requirements.append(
                    ("Head pose", bool(statuses.get("one_camera_head_pose")))
                )

        if getattr(mode_cls, "requires_facial_gesture_calibration", False):
            requirements.append(
                ("Facial gestures", bool(statuses.get("facial_gestures")))
            )

        if getattr(mode_cls, "requires_stereo_calibration", False):
            requirements.append(("Stereo", bool(statuses.get("stereo"))))

        if getattr(mode_cls, "requires_gaze_calibration", False):
            requirements.append(("Gaze", bool(statuses.get("eye_gaze"))))

        if not requirements:
            requirements.append(("None", True))

        return requirements
