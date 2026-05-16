from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QFormLayout, QLabel, QVBoxLayout, QWidget

from criteria.core import theme
from criteria.core.storage import APP_DATA_DIR
from criteria.ui.components.cards import card

class SettingsPage(QWidget):
    theme_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        title = QLabel("Settings")
        title.setObjectName("Title")
        layout.addWidget(title)

        appearance, appearance_layout = card()
        appearance_layout.addWidget(QLabel("Appearance"))
        form = QFormLayout()
        form.setSpacing(12)
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Light", "light")
        self.theme_combo.addItem("Dark", "dark")
        index = self.theme_combo.findData(theme.active_name())
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        form.addRow("Theme", self.theme_combo)
        appearance_layout.addLayout(form)
        layout.addWidget(appearance)

        info, info_layout = card()
        text = QLabel(
            "MVP task defaults: Movement 15 trials, Accuracy 12 trials, "
            "Tracking 30 seconds at 30 Hz, Clicking 12 trials.\n\n"
            f"Data folder:\n{APP_DATA_DIR}"
        )
        text.setWordWrap(True)
        info_layout.addWidget(text)
        layout.addWidget(info)
        layout.addStretch(1)

    def _on_theme_changed(self) -> None:
        name = self.theme_combo.currentData()
        if name:
            self.theme_changed.emit(name)
