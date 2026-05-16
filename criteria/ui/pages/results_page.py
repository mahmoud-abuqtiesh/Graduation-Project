from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from typing import Any

from criteria.core import theme
from criteria.core.advanced_metrics import compute_advanced_metrics
from criteria.core.models import Batch, Session
from criteria.ui.components.cards import card

def _fmt(value: Any, suffix: str = "") -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.2f}{suffix}"
    return f"{value}{suffix}"

def _format_advanced(adv: dict[str, dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    m = adv.get("movement", {})
    if m.get("nominal_throughput_bps") is not None:
        tp_str = f"Throughput {_fmt(m['nominal_throughput_bps'])} bits/s"
        if m.get("effective_throughput_bps") is not None:
            tp_str += f"  (effective: {_fmt(m['effective_throughput_bps'])} bits/s)"
        lines.append(f"Movement:  {tp_str}  |  Mean ID {_fmt(m['mean_index_of_difficulty'])}")
    a = adv.get("accuracy", {})
    if a.get("precision_2d_px") is not None:
        lines.append(
            f"Accuracy:  Precision {_fmt(a['precision_2d_px'])} px  |  "
            f"Bias {_fmt(a['bias_magnitude_px'])} px  |  "
            f"RMS Error {_fmt(a['rms_pixel_error'])} px"
        )
    t = adv.get("tracking", {})
    if t.get("pct_time_on_target") is not None:
        pct = t["pct_time_on_target"] * 100
        lines.append(
            f"Tracking:  On Target {pct:.1f}%  |  "
            f"Path Efficiency {_fmt(t['path_efficiency'])}  |  "
            f"Speed {_fmt(t['mean_cursor_speed_px_per_s'])} px/s"
        )
    c = adv.get("clicking", {})
    if c.get("median_time_to_click_ms") is not None:
        lines.append(f"Clicking:  Median RT {_fmt(c['median_time_to_click_ms'])} ms")
    return lines

class ResultsPage(QWidget):
    export_json_requested = Signal(str)
    export_csv_requested = Signal(str)
    export_simple_csv_requested = Signal(str)
    export_all_csv_requested = Signal()
    export_all_simple_csv_requested = Signal()
    export_batch_csv_requested = Signal(str)
    remove_session_from_batch_requested = Signal(str, str)

    def __init__(self) -> None:
        super().__init__()
        self.sessions: list[Session] = []
        self.batches: list[Batch] = []
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        title = QLabel("Results")
        title.setObjectName("Title")
        outer.addWidget(title)
        export_row = QHBoxLayout()
        export_all_btn = QPushButton("Export All Sessions as CSV")
        export_all_btn.setFixedWidth(260)
        export_all_btn.clicked.connect(self.export_all_csv_requested.emit)
        export_row.addWidget(export_all_btn)
        export_all_simple_btn = QPushButton("Export All as Simple CSV")
        export_all_simple_btn.setFixedWidth(260)
        export_all_simple_btn.setProperty("secondary", True)
        export_all_simple_btn.clicked.connect(self.export_all_simple_csv_requested.emit)
        export_row.addWidget(export_all_simple_btn)
        export_row.addStretch(1)
        outer.addLayout(export_row)

        batches_header = QLabel("Batches")
        batches_header.setStyleSheet("font-size: 16px; font-weight: 700; margin-top: 8px;")
        outer.addWidget(batches_header)
        self.batches_container = QWidget()
        self.batches_layout = QVBoxLayout(self.batches_container)
        self.batches_layout.setContentsMargins(0, 0, 0, 0)
        self.batches_layout.setSpacing(8)
        outer.addWidget(self.batches_container)

        sessions_header = QLabel("Individual Sessions")
        sessions_header.setStyleSheet("font-size: 16px; font-weight: 700; margin-top: 8px;")
        outer.addWidget(sessions_header)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.container = QWidget()
        self.layout = QVBoxLayout(self.container)
        self.layout.setSpacing(14)
        self.layout.addStretch(1)
        scroll.setWidget(self.container)
        outer.addWidget(scroll)

        theme.register_listener(self._reapply_theme)

    def _reapply_theme(self) -> None:
        self.set_sessions(self.sessions)
        self.set_batches(self.batches)

    def set_batches(self, batches: list[Batch]) -> None:
        self.batches = batches
        sessions_by_id = {s.session_id: s for s in self.sessions}
        palette = theme.get_palette()
        while self.batches_layout.count():
            item = self.batches_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        if not batches:
            empty = QLabel("No batches yet. Start one from the Dashboard to group sessions.")
            empty.setStyleSheet(f"color: {palette['text_muted']}; font-style: italic;")
            self.batches_layout.addWidget(empty)
            return
        for batch in batches:
            frame, frame_layout = card()
            count = len(batch.session_ids)
            noun = "session" if count == 1 else "sessions"
            if batch.target_session_count > 0:
                progress = f"{count}/{batch.target_session_count} {noun}"
            else:
                progress = f"{count} {noun}"
            state = "active" if batch.ended_at is None else f"ended {batch.ended_at}"
            heading = QLabel(f"{batch.name} | {progress} | {state}")
            heading_color = palette["accent_green"] if batch.ended_at is None else palette["text"]
            heading.setStyleSheet(f"font-size: 15px; font-weight: 600; color: {heading_color};")
            details = QLabel(f"ID: {batch.batch_id} | started {batch.started_at}")
            details.setStyleSheet(f"color: {palette['text_muted']}; font-size: 12px;")
            details.setWordWrap(True)
            frame_layout.addWidget(heading)
            frame_layout.addWidget(details)
            if batch.session_ids:
                list_label = QLabel("Sessions in this batch:")
                list_label.setStyleSheet(
                    f"color: {palette['text_muted']}; font-size: 12px; margin-top: 4px;"
                )
                frame_layout.addWidget(list_label)
                for session_id in batch.session_ids:
                    session = sessions_by_id.get(session_id)
                    row = QHBoxLayout()
                    if session is None:
                        text = f"{session_id} (missing)"
                    else:
                        score = session.final_summary.get("final_score", "—")
                        suffix = " [aborted]" if session.status == "aborted" else ""
                        text = f"{session.participant_name} | {session.input_method} | score {score}{suffix}"
                    row_label = QLabel(text)
                    if session is not None and session.status == "aborted":
                        row_label.setStyleSheet(
                            f"color: {palette['danger']}; font-style: italic;"
                        )
                    else:
                        row_label.setStyleSheet(f"color: {palette['text']};")
                    remove_btn = QPushButton("Remove")
                    remove_btn.setProperty("danger", True)
                    remove_btn.setFixedWidth(90)
                    remove_btn.clicked.connect(
                        lambda _, bid=batch.batch_id, sid=session_id:
                        self.remove_session_from_batch_requested.emit(bid, sid)
                    )
                    row.addWidget(row_label, 1)
                    row.addWidget(remove_btn)
                    frame_layout.addLayout(row)
            export_btn = QPushButton("Export Batch CSV")
            export_btn.setEnabled(count > 0)
            export_btn.clicked.connect(
                lambda _, bid=batch.batch_id: self.export_batch_csv_requested.emit(bid)
            )
            frame_layout.addWidget(export_btn)
            self.batches_layout.addWidget(frame)

    def set_sessions(self, sessions: list[Session]) -> None:
        self.sessions = sessions
        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        if not sessions:
            self.layout.addWidget(QLabel("No sessions available."))
            self.layout.addStretch(1)
            return
        palette = theme.get_palette()
        for session in sessions:
            frame, frame_layout = card()
            summary = session.final_summary or {}
            score = summary.get("final_score", "N/A")
            label = summary.get("quality_label", "N/A")
            heading = QLabel(f"{session.participant_name} | {session.input_method}")
            heading.setStyleSheet("font-size: 18px; font-weight: 700;")
            score_label = QLabel(f"Final Score: {score} / 100 | Rating: {label}")
            details = QLabel(
                f"Seed: {session.seed} | Screen: {session.screen_width}x{session.screen_height} | "
                f"Status: {session.status} | Started: {session.started_at}"
            )
            details.setWordWrap(True)
            frame_layout.addWidget(heading)
            frame_layout.addWidget(score_label)
            frame_layout.addWidget(details)
            if session.tags:
                tags_str = ", ".join(f"{k}={v}" for k, v in session.tags.items())
                tags_label = QLabel(f"Tags: {tags_str}")
                tags_label.setWordWrap(True)
                tags_label.setStyleSheet(f"color: {palette['text_muted']}; font-size: 12px;")
                frame_layout.addWidget(tags_label)
            for task_id in ("movement", "accuracy", "tracking", "clicking"):
                result = session.task_results.get(task_id)
                value = result.score if result else "N/A"
                frame_layout.addWidget(QLabel(f"{task_id.title()}: {value}"))
            adv = compute_advanced_metrics(session)
            adv_lines = _format_advanced(adv)
            if adv_lines:
                separator = QLabel("")
                separator.setFixedHeight(2)
                separator.setStyleSheet(
                    f"background: {palette['separator']}; margin: 4px 0;"
                )
                frame_layout.addWidget(separator)
                adv_header = QLabel("Advanced Metrics")
                adv_header.setStyleSheet(
                    f"font-size: 14px; font-weight: 600; color: {palette['text_muted']};"
                )
                frame_layout.addWidget(adv_header)
                for line in adv_lines:
                    lbl = QLabel(line)
                    lbl.setStyleSheet(f"color: {palette['text_muted']}; font-size: 13px;")
                    lbl.setWordWrap(True)
                    frame_layout.addWidget(lbl)
            json_button = QPushButton("Export JSON")
            csv_button = QPushButton("Export CSV Summary")
            csv_button.setProperty("secondary", True)
            simple_csv_button = QPushButton("Export Simple CSV")
            simple_csv_button.setProperty("secondary", True)
            json_button.clicked.connect(lambda _, sid=session.session_id: self.export_json_requested.emit(sid))
            csv_button.clicked.connect(lambda _, sid=session.session_id: self.export_csv_requested.emit(sid))
            simple_csv_button.clicked.connect(lambda _, sid=session.session_id: self.export_simple_csv_requested.emit(sid))
            frame_layout.addWidget(json_button)
            frame_layout.addWidget(csv_button)
            frame_layout.addWidget(simple_csv_button)
            self.layout.addWidget(frame)
        self.layout.addStretch(1)

