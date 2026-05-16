from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from criteria.core import theme
from criteria.core.models import Session
from criteria.core.storage import StorageManager
from criteria.ui.pages.dashboard_page import DashboardPage
from criteria.ui.pages.metrics_guide_page import MetricsGuidePage
from criteria.ui.pages.results_page import ResultsPage
from criteria.ui.pages.resume_page import ResumePage
from criteria.ui.pages.session_setup_page import SessionSetupPage
from criteria.ui.pages.settings_page import SettingsPage
from criteria.ui.test_window import TestWindow

class StartBatchDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Start Batch")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Eye Gaze — Mahmoud — May 8")
        self.target_spin = QSpinBox()
        self.target_spin.setRange(0, 1000)
        self.target_spin.setValue(10)
        self.target_spin.setSpecialValueText("No target")
        form.addRow("Batch name", self.name_edit)
        form.addRow("Target runs", self.target_spin)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> tuple[str, int]:
        return self.name_edit.text().strip(), int(self.target_spin.value())

class MainWindow(QMainWindow):
    def __init__(self, storage: StorageManager | None = None) -> None:
        super().__init__()
        self.storage = storage or StorageManager()
        self.test_window: TestWindow | None = None
        self.setWindowTitle("EyeCursor TestLab")
        self.setMinimumSize(1040, 680)
        self.resize(1160, 760)
        icon = Path(__file__).resolve().parents[2] / "assets" / "icon_256.png"
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))
        self._setup_ui()
        self._connect()
        self._setup_shortcuts()
        self.refresh()

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(210)
        for name in ["Dashboard", "New Session", "Resume Session", "Results", "Metrics Guide", "Settings"]:
            self.sidebar.addItem(QListWidgetItem(name))
        layout.addWidget(self.sidebar)
        self.stack = QStackedWidget()
        self.dashboard = DashboardPage()
        self.setup_page = SessionSetupPage()
        self.resume_page = ResumePage()
        self.results_page = ResultsPage()
        self.metrics_guide_page = MetricsGuidePage()
        self.settings_page = SettingsPage()
        for page in (self.dashboard, self.setup_page, self.resume_page, self.results_page, self.metrics_guide_page, self.settings_page):
            self.stack.addWidget(page)
        layout.addWidget(self.stack)
        self.sidebar.setCurrentRow(0)

    def _connect(self) -> None:
        self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.sidebar.currentRowChanged.connect(self._on_page_changed)
        self.dashboard.new_requested.connect(self._open_new_session)
        self.dashboard.resume_requested.connect(lambda: self.sidebar.setCurrentRow(2))
        self.dashboard.results_requested.connect(lambda: self.sidebar.setCurrentRow(3))
        self.dashboard.start_batch_requested.connect(self.start_batch)
        self.dashboard.end_batch_requested.connect(self.end_batch)
        self.setup_page.session_created.connect(self.start_session)
        self.resume_page.resume_selected.connect(self.resume_session)
        self.results_page.export_json_requested.connect(self.export_json)
        self.results_page.export_csv_requested.connect(self.export_csv)
        self.results_page.export_simple_csv_requested.connect(self.export_simple_csv)
        self.results_page.export_all_csv_requested.connect(self.export_all_csv)
        self.results_page.export_all_simple_csv_requested.connect(self.export_all_simple_csv)
        self.results_page.export_batch_csv_requested.connect(self.export_batch_csv)
        self.results_page.remove_session_from_batch_requested.connect(self.remove_session_from_batch)
        self.settings_page.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, name: str) -> None:
        self.storage.set_theme(name)
        app = QApplication.instance()
        if app is not None:
            theme.apply_theme(app, name)

    def _setup_shortcuts(self) -> None:
        new_shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        new_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        new_shortcut.activated.connect(self._open_new_session)

    def _open_new_session(self) -> None:
        self._prefill_setup_page()
        self.sidebar.setCurrentRow(1)

    def _prefill_setup_page(self) -> None:
        sessions = self.storage.list_sessions()
        last = sessions[0] if sessions else None
        self.setup_page.prefill_from(last)

    def _on_page_changed(self, index: int) -> None:
        if index == 1:
            self._prefill_setup_page()

    def refresh(self) -> None:
        sessions = self.storage.list_sessions()
        active_batch = self.storage.get_active_batch()
        batches = self.storage.list_batches()
        self.dashboard.set_recent(sessions)
        self.dashboard.set_active_batch(active_batch)
        self.resume_page.set_sessions(sessions)
        self.results_page.set_sessions(sessions)
        self.results_page.set_batches(batches)
        if active_batch is not None:
            count = len(active_batch.session_ids)
            target = active_batch.target_session_count
            progress = f" — {active_batch.name} ({count}/{target})" if target else f" — {active_batch.name} ({count})"
            self.setWindowTitle(f"EyeCursor TestLab{progress}")
        else:
            self.setWindowTitle("EyeCursor TestLab")

    def start_batch(self) -> None:
        if self.storage.get_active_batch() is not None:
            QMessageBox.information(self, "Batch already active", "End the current batch before starting a new one.")
            return
        dialog = StartBatchDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        name, target = dialog.values()
        if not name:
            QMessageBox.warning(self, "Batch needs a name", "Please enter a name for the batch.")
            return
        try:
            self.storage.start_batch(name, target_session_count=target)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Could not start batch", str(exc))
            return
        self.refresh()

    def end_batch(self) -> None:
        batch = self.storage.get_active_batch()
        if batch is None:
            QMessageBox.information(self, "No active batch", "There is no active batch to end.")
            return
        confirm = QMessageBox.question(
            self,
            "End Batch",
            f"End batch '{batch.name}'? You can export its CSV from the Results page.",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            self.storage.end_active_batch()
        except OSError as exc:
            QMessageBox.critical(self, "Could not end batch", str(exc))
            return
        self.refresh()

    def start_session(self, session: Session) -> None:
        try:
            self.storage.add_session_to_active_batch(session)
            self.storage.save_session(session)
            self._open_test_window(session)
        except OSError:
            QMessageBox.critical(
                self,
                "Could not save session",
                "Could not save the session results. Check that the app has permission to write to the results folder.",
            )

    def resume_session(self, session_id: str) -> None:
        try:
            session = self.storage.load_session(session_id)
        except (OSError, ValueError, TypeError) as exc:
            QMessageBox.critical(self, "Could not resume session", str(exc))
            return
        self._open_test_window(session)

    def export_json(self, session_id: str) -> None:
        try:
            path = self.storage.export_json(self.storage.load_session(session_id))
        except OSError:
            QMessageBox.critical(self, "Export failed", "Could not export the raw JSON session.")
            return
        QMessageBox.information(self, "Export complete", f"JSON exported to:\n{path}")

    def export_csv(self, session_id: str) -> None:
        try:
            path = self.storage.export_summary_csv(self.storage.load_session(session_id))
        except OSError:
            QMessageBox.critical(self, "Export failed", "Could not export the CSV summary.")
            return
        QMessageBox.information(self, "Export complete", f"CSV exported to:\n{path}")

    def export_all_csv(self) -> None:
        try:
            path = self.storage.export_all_sessions_csv()
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        QMessageBox.information(self, "Export complete", f"All sessions exported to:\n{path}")

    def export_simple_csv(self, session_id: str) -> None:
        try:
            session = self.storage.load_session(session_id)
            path = self.storage.export_simple_csv([session])
        except (OSError, ValueError, FileNotFoundError) as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        QMessageBox.information(self, "Export complete", f"Simple CSV exported to:\n{path}")

    def export_all_simple_csv(self) -> None:
        try:
            sessions = self.storage.list_sessions()
            path = self.storage.export_simple_csv(sessions)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        QMessageBox.information(self, "Export complete", f"All sessions simple CSV exported to:\n{path}")

    def export_batch_csv(self, batch_id: str) -> None:
        try:
            path = self.storage.export_batch_csv(batch_id)
        except (OSError, ValueError, FileNotFoundError) as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        QMessageBox.information(self, "Export complete", f"Batch CSV exported to:\n{path}")

    def remove_session_from_batch(self, batch_id: str, session_id: str) -> None:
        confirm = QMessageBox.question(
            self,
            "Remove session from batch",
            "Remove this session from the batch? The session itself will be kept.",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            self.storage.remove_session_from_batch(batch_id, session_id)
        except (OSError, FileNotFoundError) as exc:
            QMessageBox.critical(self, "Could not remove session", str(exc))
            return
        self.refresh()

    def _open_test_window(self, session: Session) -> None:
        self.test_window = TestWindow(session, self.storage)
        self.test_window.closed.connect(self.refresh)
        self.test_window.results_requested.connect(lambda: self.sidebar.setCurrentRow(3))
        self.test_window.begin()
