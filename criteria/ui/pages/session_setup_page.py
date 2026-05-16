from __future__ import annotations

import random

from PySide6.QtCore import Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from criteria.core import theme
from criteria.core.models import Session, TaskConfig
from criteria.ui.components.cards import card

PRESET_METHODS = ["Mouse", "One-Camera Head Pose", "Two-Camera Head Pose", "Eye-Gaze Only", "Custom"]

class TagEditor(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self._rows_container = QWidget()
        self._rows_layout = QVBoxLayout(self._rows_container)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(4)
        layout.addWidget(self._rows_container)
        add_btn = QPushButton("+ Add tag")
        add_btn.setProperty("secondary", True)
        add_btn.clicked.connect(lambda: self.add_row())
        layout.addWidget(add_btn, 0)

    def add_row(self, key: str = "", value: str = "") -> None:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)
        key_edit = QLineEdit(key)
        key_edit.setPlaceholderText("key (e.g. distance_m)")
        value_edit = QLineEdit(value)
        value_edit.setPlaceholderText("value (e.g. 0.75)")
        remove_btn = QPushButton("−")
        remove_btn.setFixedWidth(30)
        remove_btn.setProperty("danger", True)
        remove_btn.clicked.connect(lambda: self._remove_row(row))
        row_layout.addWidget(key_edit, 1)
        row_layout.addWidget(value_edit, 1)
        row_layout.addWidget(remove_btn, 0)
        row.key_edit = key_edit
        row.value_edit = value_edit
        self._rows_layout.addWidget(row)

    def _remove_row(self, row: QWidget) -> None:
        self._rows_layout.removeWidget(row)
        row.deleteLater()

    def clear(self) -> None:
        while self._rows_layout.count():
            item = self._rows_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def tags(self) -> dict[str, str]:
        result: dict[str, str] = {}
        for i in range(self._rows_layout.count()):
            row = self._rows_layout.itemAt(i).widget()
            if row is None:
                continue
            key = row.key_edit.text().strip()
            value = row.value_edit.text().strip()
            if not key:
                continue
            result[key] = value
        return result

class SessionSetupPage(QWidget):
    session_created = Signal(Session)

    def __init__(self) -> None:
        super().__init__()
        self._current_seed = random.randint(1, 999_999)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel("New Session")
        title.setObjectName("Title")
        layout.addWidget(title)

        frame, form_layout = card()
        form = QFormLayout()
        form.setSpacing(12)
        self.participant = QLineEdit()
        self.participant.setPlaceholderText("Participant name or ID")
        self.input_method = QComboBox()
        self.input_method.addItems(PRESET_METHODS)
        self.custom_method = QLineEdit()
        self.custom_method.setPlaceholderText("Custom input method label")
        self.seed_label = QLabel(str(self._current_seed))
        self._refresh_seed_style()
        theme.register_listener(self._refresh_seed_style)
        self.tag_editor = TagEditor()
        screen = QGuiApplication.primaryScreen().geometry()
        self.screen_label = QLabel(f"{screen.width()} x {screen.height()} px")
        self.preset_label = QLabel("MVP Default")
        form.addRow("Participant", self.participant)
        form.addRow("Input Method", self.input_method)
        form.addRow("Custom Label", self.custom_method)
        form.addRow("Seed (auto)", self.seed_label)
        form.addRow("Screen Resolution", self.screen_label)
        form.addRow("Task Preset", self.preset_label)
        form.addRow("Tags", self.tag_editor)
        form_layout.addLayout(form)
        layout.addWidget(frame)

        start = QPushButton("Start Fullscreen Test")
        start.clicked.connect(self._create_session)
        layout.addWidget(start)
        layout.addStretch(1)

    def _refresh_seed_style(self) -> None:
        self.seed_label.setStyleSheet(f"color: {theme.get_palette()['text_muted']};")

    def prefill_from(self, session: Session | None) -> None:
        self._current_seed = random.randint(1, 999_999)
        self.seed_label.setText(str(self._current_seed))
        self.tag_editor.clear()
        if session is None:
            return
        self.participant.setText(session.participant_name)
        method = session.input_method
        if method in PRESET_METHODS:
            self.input_method.setCurrentText(method)
            self.custom_method.clear()
        else:
            self.input_method.setCurrentText("Custom")
            self.custom_method.setText(method)
        for key, value in session.tags.items():
            self.tag_editor.add_row(key, value)

    def _create_session(self) -> None:
        screen = QGuiApplication.primaryScreen().geometry()
        method = self.input_method.currentText()
        if method == "Custom":
            method = self.custom_method.text().strip() or "Custom"
        session = Session.create(
            participant_name=self.participant.text(),
            input_method=method,
            seed=self._current_seed,
            screen_width=screen.width(),
            screen_height=screen.height(),
            tags=self.tag_editor.tags(),
            task_config=TaskConfig(),
        )
        self.session_created.emit(session)
