from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from criteria.core import theme
from criteria.core.models import Batch, Session
from criteria.ui.components.cards import card

class DashboardPage(QWidget):
    new_requested = Signal()
    resume_requested = Signal()
    results_requested = Signal()
    start_batch_requested = Signal()
    end_batch_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel("EyeCursor TestLab")
        title.setObjectName("Title")
        subtitle = QLabel("Repeatable fullscreen cursor behavior tests for movement, accuracy, tracking, and clicking.")
        subtitle.setObjectName("Subtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        actions, action_layout = card()
        start = QPushButton("Start New Session")
        resume = QPushButton("Resume Session")
        results = QPushButton("View Results")
        resume.setProperty("secondary", True)
        results.setProperty("secondary", True)
        start.clicked.connect(self.new_requested.emit)
        resume.clicked.connect(self.resume_requested.emit)
        results.clicked.connect(self.results_requested.emit)
        action_layout.addWidget(start)
        action_layout.addWidget(resume)
        action_layout.addWidget(results)
        layout.addWidget(actions)

        batch_card, batch_layout = card()
        batch_layout.addWidget(QLabel("Batch"))
        self.batch_status_label = QLabel("No active batch.")
        self.batch_status_label.setWordWrap(True)
        batch_layout.addWidget(self.batch_status_label)
        batch_buttons = QHBoxLayout()
        self.start_batch_btn = QPushButton("Start Batch")
        self.end_batch_btn = QPushButton("End Batch")
        self.end_batch_btn.setProperty("secondary", True)
        self.start_batch_btn.clicked.connect(self.start_batch_requested.emit)
        self.end_batch_btn.clicked.connect(self.end_batch_requested.emit)
        batch_buttons.addWidget(self.start_batch_btn)
        batch_buttons.addWidget(self.end_batch_btn)
        batch_buttons.addStretch(1)
        batch_layout.addLayout(batch_buttons)
        layout.addWidget(batch_card)

        self.recent_label = QLabel("No sessions yet.")
        self.recent_label.setWordWrap(True)
        recent, recent_layout = card()
        recent_layout.addWidget(QLabel("Recent Session"))
        recent_layout.addWidget(self.recent_label)
        layout.addWidget(recent)
        layout.addStretch(1)

        self._active_batch: Batch | None = None
        theme.register_listener(self._reapply_theme)

    def set_recent(self, sessions: list[Session]) -> None:
        if not sessions:
            self.recent_label.setText("No sessions yet.")
            return
        session = sessions[0]
        score = session.final_summary.get("final_score", "N/A")
        self.recent_label.setText(
            f"{session.participant_name} | {session.input_method} | "
            f"{session.status} | Score: {score}"
        )

    def set_active_batch(self, batch: Batch | None) -> None:
        self._active_batch = batch
        palette = theme.get_palette()
        if batch is None:
            self.batch_status_label.setText(
                "No active batch. New sessions will not be grouped."
            )
            self.batch_status_label.setStyleSheet(f"color: {palette['text_muted']};")
            self.start_batch_btn.setEnabled(True)
            self.end_batch_btn.setEnabled(False)
            return
        count = len(batch.session_ids)
        noun = "session" if count == 1 else "sessions"
        if batch.target_session_count > 0:
            progress = f"{count}/{batch.target_session_count} {noun}"
        else:
            progress = f"{count} {noun}"
        self.batch_status_label.setText(
            f"Active batch: {batch.name} | {progress} | started {batch.started_at}"
        )
        self.batch_status_label.setStyleSheet(
            f"color: {palette['accent_green']}; font-weight: 600;"
        )
        self.start_batch_btn.setEnabled(False)
        self.end_batch_btn.setEnabled(True)

    def _reapply_theme(self) -> None:
        self.set_active_batch(self._active_batch)
