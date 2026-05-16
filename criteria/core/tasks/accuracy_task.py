from __future__ import annotations

from PySide6.QtCore import QPointF, QRect
from PySide6.QtGui import QColor, QFont, QPainter, QPen

from criteria.core import theme
from criteria.core.metrics import avg, distance, med
from criteria.core.scoring import accuracy_score
from criteria.core.sounds import play as sfx
from criteria.core.tasks.base_task import TestTask

class AccuracyTask(TestTask):
    id = "accuracy"
    display_name = "Accuracy"
    description = "Get as close as possible to the center before time expires."

    radius = 60
    timeout_ms = 4000
    dwell_ms = 400

    def start(self, bounds: QRect) -> None:
        super().start(bounds)
        self.trial_index = 0
        self.current_started_ms = 0
        self.target = self.target_from_rng(self.radius)
        self.last_cursor = QPointF(self.screen_width / 2, self.screen_height / 2)
        self._inside_since_ms: int | None = None
        self._warning_played = False

    def update(self, elapsed_ms: int, cursor: QPointF) -> None:
        super().update(elapsed_ms, cursor)
        self.last_cursor = cursor
        if self.completed or self.paused:
            return
        inside = self.point_inside(self.target, cursor)
        if inside:
            if self._inside_since_ms is None:
                self._inside_since_ms = elapsed_ms
                sfx("ding")
            elif elapsed_ms - self._inside_since_ms >= self.dwell_ms:
                self._finish_trial(elapsed_ms, dwell_success=True)
                return
        else:
            self._inside_since_ms = None
        trial_remaining = self.timeout_ms - (elapsed_ms - self.current_started_ms)
        if not self._warning_played and trial_remaining <= 300:
            sfx("tick")
            self._warning_played = True
        if elapsed_ms - self.current_started_ms >= self.timeout_ms:
            self._finish_trial(elapsed_ms, dwell_success=False)

    def paint(self, painter: QPainter, rect: QRect) -> None:
        palette = theme.get_palette()
        painter.fillRect(rect, QColor(palette["background"]))
        fill_color = palette["accent_green"] if self._inside_since_ms is not None else palette["primary"]
        self.draw_target(painter, self.target, fill_color)
        painter.setPen(QPen(QColor(palette["text"])))
        painter.setFont(QFont("Arial", 16))
        painter.drawText(28, 42, f"Accuracy {self.trial_index + 1}/{self.config.accuracy_trials}")
        painter.drawText(28, 72, f"{max(0, self.timeout_ms - (self.elapsed_ms - self.current_started_ms)) / 1000:.1f}s")
        if self._inside_since_ms is not None:
            held_ms = self.elapsed_ms - self._inside_since_ms
            painter.drawText(28, 102, f"Hold {min(held_ms, self.dwell_ms)}/{self.dwell_ms} ms")

    def _finish_trial(self, elapsed_ms: int, dwell_success: bool) -> None:
        pixel_error = distance(self.last_cursor.x(), self.last_cursor.y(), self.target.x, self.target.y)
        time_to_dwell_ms = (
            (self._inside_since_ms - self.current_started_ms + self.dwell_ms)
            if dwell_success and self._inside_since_ms is not None
            else None
        )
        self.raw.append(
            {
                "task": self.id,
                "trial_index": self.trial_index,
                "target_x": round(self.target.x, 2),
                "target_y": round(self.target.y, 2),
                "target_radius": self.radius,
                "cursor_x": round(self.last_cursor.x(), 2),
                "cursor_y": round(self.last_cursor.y(), 2),
                "pixel_error": round(pixel_error, 3),
                "radius_normalized_error": round(pixel_error / self.radius, 5),
                "screen_normalized_error": round(pixel_error / self.screen_diagonal_px, 7),
                "timeout_ms": self.timeout_ms,
                "dwell_ms": self.dwell_ms,
                "dwell_success": dwell_success,
                "time_to_dwell_ms": time_to_dwell_ms,
                "end_time_ms": elapsed_ms,
            }
        )
        if dwell_success:
            sfx("success")
        self.trial_index += 1
        self.current_started_ms = elapsed_ms
        self._inside_since_ms = None
        self._warning_played = False
        if self.trial_index >= self.config.accuracy_trials:
            self._summarize()
            self.completed = True
        else:
            self.target = self.target_from_rng(self.radius)

    def _summarize(self) -> None:
        pixel_errors = [row["pixel_error"] for row in self.raw]
        radius_errors = [row["radius_normalized_error"] for row in self.raw]
        screen_errors = [row["screen_normalized_error"] for row in self.raw]
        successes = [row for row in self.raw if row["dwell_success"]]
        dwell_times = [row["time_to_dwell_ms"] for row in successes if row["time_to_dwell_ms"] is not None]
        avg_radius = avg(radius_errors)
        self.score = accuracy_score(avg_radius)
        success_rate = (len(successes) / len(self.raw)) if self.raw else 0.0
        self.summary = {
            "average_pixel_error": round(avg(pixel_errors), 3),
            "median_pixel_error": round(med(pixel_errors), 3),
            "average_radius_normalized_error": round(avg_radius, 5),
            "median_radius_normalized_error": round(med(radius_errors), 5),
            "average_screen_normalized_error": round(avg(screen_errors), 7),
            "dwell_ms": self.dwell_ms,
            "dwell_success_count": len(successes),
            "dwell_success_rate": round(success_rate, 3),
            "median_time_to_dwell_ms": round(med(dwell_times), 1) if dwell_times else None,
            "accuracy_score": self.score,
        }

