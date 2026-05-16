from __future__ import annotations

from PySide6.QtCore import QPointF, QRect, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen

from criteria.core import theme
from criteria.core.scoring import clicking_score
from criteria.core.sounds import play as sfx
from criteria.core.tasks.base_task import TestTask

class ClickingTask(TestTask):
    id = "clicking"
    display_name = "Clicking"
    description = "Click the requested mouse button before time expires."

    timeout_ms = 5000

    def start(self, bounds: QRect) -> None:
        super().start(bounds)
        self.trial_index = 0
        self.current_started_ms = 0
        self.requested_click = self._next_click_type()
        self._warning_played = False

    def update(self, elapsed_ms: int, cursor: QPointF) -> None:
        super().update(elapsed_ms, cursor)
        if self.completed or self.paused:
            return
        trial_remaining = self.timeout_ms - (elapsed_ms - self.current_started_ms)
        if not self._warning_played and trial_remaining <= 2000:
            sfx("warning")
            self._warning_played = True
        if elapsed_ms - self.current_started_ms >= self.timeout_ms:
            self._record_trial(elapsed_ms, QPointF(-1, -1), None, "timeout")

    def mouse_press(self, elapsed_ms: int, pos: QPointF, button: str) -> None:
        super().mouse_press(elapsed_ms, pos, button)
        if self.completed or self.paused:
            return
        if button == self.requested_click:
            result = "success"
            sfx("success")
        else:
            result = "fail_wrong_button"
            sfx("error")
        self._record_trial(elapsed_ms, pos, button, result)

    def paint(self, painter: QPainter, rect: QRect) -> None:
        palette = theme.get_palette()
        painter.fillRect(rect, QColor(palette["background"]))
        accent = palette["accent_cyan"] if self.requested_click == "left" else palette["accent_orange"]
        painter.setPen(QPen(QColor(accent)))
        painter.setFont(QFont("Arial", 96, QFont.Weight.Black))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{self.requested_click.upper()} CLICK")
        painter.setPen(QPen(QColor(palette["text"])))
        painter.setFont(QFont("Arial", 16))
        painter.drawText(28, 44, f"Clicking {self.trial_index + 1}/{self.config.clicking_trials}")
        painter.drawText(28, 74, f"{max(0, self.timeout_ms - (self.elapsed_ms - self.current_started_ms)) / 1000:.1f}s")

    def _next_click_type(self) -> str:
        return "left" if self.random.random() < 0.5 else "right"

    def _record_trial(
        self,
        elapsed_ms: int,
        pos: QPointF,
        button: str | None,
        result: str,
    ) -> None:
        self.raw.append(
            {
                "task": self.id,
                "trial_index": self.trial_index,
                "requested_click": self.requested_click,
                "actual_click": button,
                "click_x": round(pos.x(), 2) if button else None,
                "click_y": round(pos.y(), 2) if button else None,
                "result": result,
                "time_to_click_ms": elapsed_ms - self.current_started_ms if button else None,
            }
        )
        self.trial_index += 1
        self.current_started_ms = elapsed_ms
        self._warning_played = False
        if self.trial_index >= self.config.clicking_trials:
            self._summarize()
            self.completed = True
        else:
            self.requested_click = self._next_click_type()

    def _summarize(self) -> None:
        total = len(self.raw) or 1
        success = sum(1 for row in self.raw if row["result"] == "success")
        wrong_button = sum(1 for row in self.raw if row["result"] == "fail_wrong_button")
        timeouts = sum(1 for row in self.raw if row["result"] == "timeout")
        success_rate = success / total
        wrong_button_rate = wrong_button / total
        timeout_rate = timeouts / total
        self.score = clicking_score(success_rate, wrong_button_rate, timeout_rate)
        self.summary = {
            "trial_count": len(self.raw),
            "success_count": success,
            "wrong_button_count": wrong_button,
            "timeout_count": timeouts,
            "success_rate": round(success_rate, 4),
            "wrong_button_rate": round(wrong_button_rate, 4),
            "timeout_rate": round(timeout_rate, 4),
            "clicking_score": self.score,
        }
