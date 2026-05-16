import sys

from PySide6.QtWidgets import QApplication

from src.app.bootstrap import initialize_app

def main() -> int:
    if sys.platform == "win32":
        import ctypes
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "EyeCursorTeam.EyeCursor.App.1"
            )
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("EyeCursor")
    app.setOrganizationName("EyeCursorTeam")

    window = initialize_app()

    if sys.platform == "win32":
        from pathlib import Path
        from PySide6.QtGui import QIcon

        icon_path = Path(__file__).resolve().parents[2] / "assets" / "eyecursor.ico"
        if icon_path.exists():
            icon = QIcon(str(icon_path))
            app.setWindowIcon(icon)
            window.setWindowIcon(icon)

    window.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
