from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)
from PySide6.QtCore import Signal

from src.ui.components.calibration_score import CalibrationScoreBadge

class ModeCard(QFrame):
    selected = Signal(str)

    def __init__(
        self,
        mode_id: str,
        display_name: str,
        description: str,
        calibration_requirements: list[tuple[str, bool]],
        required_cameras: int,
        calibration_label: str = "Not Ready",
        is_ready: bool = True,
        is_active: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._mode_id = mode_id
        self._is_ready = is_ready
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            "ModeCard { background: #ffffff; border: 1px solid #dcdde1; "
            "border-radius: 8px; padding: 16px; }"
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel(f"<b>{display_name}</b>")
        title.setStyleSheet("font-size: 16px; border: none;")
        header.addWidget(title)
        header.addStretch()

        self._badge = CalibrationScoreBadge(calibration_label)
        badge_width = 0
        for label in ("Not Ready", "Ready"):
            temp_badge = CalibrationScoreBadge(label)
            badge_width = max(badge_width, temp_badge.sizeHint().width())
        header.addWidget(self._badge)
        layout.addLayout(header)

        desc = QLabel(description)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #636e72; font-size: 13px; border: none;")
        layout.addWidget(desc)

        cal_row = QHBoxLayout()
        cal_label = QLabel("Requirements:")
        cal_label.setStyleSheet(
            "color: #2d3436; font-size: 12px; font-weight: 600; border: none;"
        )
        cal_row.addWidget(cal_label)

        cal_tags = QHBoxLayout()
        cal_tags.setSpacing(6)
        for label, is_ready in calibration_requirements:
            tag = QLabel(label)
            tag.setFixedHeight(18)
            if is_ready:
                tag.setStyleSheet(
                    "background: #dff5e1; color: #1b5e20; border-radius: 6px; "
                    "padding: 1px 6px; font-size: 11px;"
                )
            else:
                tag.setStyleSheet(
                    "background: #fde2e1; color: #b00020; border-radius: 6px; "
                    "padding: 1px 6px; font-size: 11px;"
                )
            cal_tags.addWidget(tag)
        cal_tags.addStretch()
        cal_row.addLayout(cal_tags)

        info_row = QHBoxLayout()
        info_row.addLayout(cal_row)
        info_row.addStretch()

        self._select_btn = QPushButton("Selected" if is_active else "Select")
        self._select_btn.setProperty("active", is_active)
        self._select_btn.setProperty("ready", self._is_ready)
        self._select_btn.setEnabled((not is_active) and self._is_ready)
        self._select_btn.setStyleSheet(
            "QPushButton { background: #0984e3; color: white; border: 1px solid #0984e3; "
            "padding: 6px 20px; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background: #0652DD; border-color: #0652DD; }"
            "QPushButton[active=\"true\"]:disabled { background: #ffffff; color: #0984e3; }"
            "QPushButton[ready=\"false\"]:disabled { background: #dfe6e9; color: #636e72; "
            "border-color: #b2bec3; }"
        )
        current_text = self._select_btn.text()
        select_width = 0
        for text in ("Selected", "Select"):
            self._select_btn.setText(text)
            select_width = max(select_width, self._select_btn.sizeHint().width())
        self._select_btn.setText(current_text)

        target_width = max(badge_width, select_width)
        if target_width:
            self._badge.setFixedWidth(target_width)
            self._select_btn.setFixedWidth(target_width)
        self._select_btn.clicked.connect(lambda: self.selected.emit(self._mode_id))
        info_row.addWidget(self._select_btn)
        layout.addLayout(info_row)

    def set_active(self, active: bool) -> None:
        self._select_btn.setText("Selected" if active else "Select")
        self._select_btn.setProperty("active", active)
        self._select_btn.style().unpolish(self._select_btn)
        self._select_btn.style().polish(self._select_btn)
        self._select_btn.setEnabled((not active) and self._is_ready)

    def set_calibration_label(self, label: str) -> None:
        self._badge.set_label(label)
