
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QWidget

_BADGE_TEXT = "IDLE"
_BADGE_BG = QColor(0xE1, 0x70, 0x55)
_DIM_OPACITY = 110

def apply_idle_overlay_to_pixmap(pix: QPixmap) -> QPixmap:
    if pix is None or pix.isNull():
        return pix
    out = QPixmap(pix)
    painter = QPainter(out)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        painter.fillRect(out.rect(), QColor(0, 0, 0, _DIM_OPACITY))

        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        text_w = metrics.horizontalAdvance(_BADGE_TEXT)
        text_h = metrics.height()
        pad_x, pad_y = 10, 4
        badge_w = text_w + 2 * pad_x
        badge_h = text_h + 2 * pad_y
        badge_x = out.width() - badge_w - 10
        badge_y = 10

        painter.setBrush(_BADGE_BG)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(badge_x, badge_y, badge_w, badge_h, 6, 6)
        painter.setPen(QColor("white"))
        painter.drawText(
            badge_x + pad_x,
            badge_y + pad_y + metrics.ascent(),
            _BADGE_TEXT,
        )
    finally:
        painter.end()
    return out

def overlay_idle_on_label(label: QLabel, idle: bool) -> None:
    if not idle or label is None:
        return
    pix = label.pixmap()
    if pix is None or pix.isNull():
        return
    label.setPixmap(apply_idle_overlay_to_pixmap(pix))

_IDLE_DIM_OPACITY = 0.45
_EFFECT_ATTR = "_idle_opacity_effect"

def dim_widget_for_idle(widget: Optional[QWidget], idle: bool) -> None:
    if widget is None:
        return
    eff = getattr(widget, _EFFECT_ATTR, None)
    if eff is None:
        eff = QGraphicsOpacityEffect(widget)
        eff.setOpacity(1.0)
        widget.setGraphicsEffect(eff)
        setattr(widget, _EFFECT_ATTR, eff)
    target = _IDLE_DIM_OPACITY if idle else 1.0
    if abs(eff.opacity() - target) > 1e-3:
        eff.setOpacity(target)
