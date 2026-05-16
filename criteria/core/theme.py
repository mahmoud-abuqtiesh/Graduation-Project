from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtWidgets import QApplication

LIGHT: dict[str, str] = {
    "background": "#f5f6fa",
    "card": "#ffffff",
    "card_border": "#e6eaee",
    "text": "#2d3436",
    "text_muted": "#636e72",
    "sidebar": "#2d3436",
    "sidebar_text": "#dfe6e9",
    "sidebar_selected": "#636e72",
    "sidebar_hover": "#4a5568",
    "primary": "#0984e3",
    "primary_hover": "#0876ca",
    "primary_pressed": "#0767b0",
    "secondary": "#636e72",
    "danger": "#d63031",
    "accent_green": "#00b894",
    "accent_purple": "#6c5ce7",
    "accent_cyan": "#00cec9",
    "accent_orange": "#e17055",
    "separator": "#dfe6e9",
    "input_bg": "#ffffff",
    "input_border": "#b2bec3",
    "target_outline": "#ffffff",
    "score_color": "#0984e3",
}

DARK: dict[str, str] = {
    "background": "#000000",
    "card": "#161616",
    "card_border": "#2a2a2a",
    "text": "#e8e8e8",
    "text_muted": "#9aa0a6",
    "sidebar": "#0a0a0a",
    "sidebar_text": "#e8e8e8",
    "sidebar_selected": "#2a2a2a",
    "sidebar_hover": "#1c1c1c",
    "primary": "#0a84ff",
    "primary_hover": "#0a78e8",
    "primary_pressed": "#0966c4",
    "secondary": "#3a3a3a",
    "danger": "#ff453a",
    "accent_green": "#30d158",
    "accent_purple": "#8e7cff",
    "accent_cyan": "#5ee3df",
    "accent_orange": "#ff8a65",
    "separator": "#2a2a2a",
    "input_bg": "#1c1c1c",
    "input_border": "#3a3a3a",
    "target_outline": "#ffffff",
    "score_color": "#0a84ff",
}

PALETTES = {"light": LIGHT, "dark": DARK}

_active_name = "light"
_listeners: list[Callable[[], None]] = []
_qss_template_cache: str | None = None

def _qss_template() -> str:
    global _qss_template_cache
    if _qss_template_cache is None:
        path = Path(__file__).resolve().parents[1] / "resources" / "styles" / "app.qss"
        _qss_template_cache = path.read_text(encoding="utf-8")
    return _qss_template_cache

def get_palette() -> dict[str, str]:
    return PALETTES[_active_name]

def active_name() -> str:
    return _active_name

def is_dark() -> bool:
    return _active_name == "dark"

def apply_theme(app: QApplication, name: str) -> None:
    global _active_name
    if name not in PALETTES:
        name = "light"
    _active_name = name
    template = _qss_template()
    app.setStyleSheet(template.format(**PALETTES[name]))
    for listener in list(_listeners):
        try:
            listener()
        except Exception:
            pass

def register_listener(callback: Callable[[], None]) -> Callable[[], None]:
    _listeners.append(callback)

    def unregister() -> None:
        if callback in _listeners:
            _listeners.remove(callback)

    return unregister
