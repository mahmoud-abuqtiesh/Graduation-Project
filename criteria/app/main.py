from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from criteria.core import theme
from criteria.core.storage import StorageManager
from criteria.ui.main_window import MainWindow

def main() -> int:
    if sys.platform == "win32":
        import ctypes
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "EyeCursorTeam.EyeCursor.TestLab.1"
            )
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("EyeCursor TestLab")
    app.setOrganizationName("EyeCursorTeam")
    storage = StorageManager()
    theme.apply_theme(app, storage.get_theme())

    window = MainWindow(storage=storage)

    if sys.platform == "win32":
        from PySide6.QtGui import QIcon

        icon_path = Path(__file__).resolve().parents[2] / "assets" / "testlab.ico"
        if icon_path.exists():
            icon = QIcon(str(icon_path))
            app.setWindowIcon(icon)
            window.setWindowIcon(icon)

    window.show()
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())
