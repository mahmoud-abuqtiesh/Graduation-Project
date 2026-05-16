from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from typing import Any

from platformdirs import user_data_dir

from criteria.core.advanced_metrics import compute_advanced_metrics
from criteria.core.models import Batch, Session, utcish_now
from criteria.core.scoring import final_summary

APP_DATA_DIR = Path(user_data_dir("EyeCursor TestLab", "EyeCursorTeam"))

class StorageManager:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or APP_DATA_DIR
        self.sessions_dir = self.base_dir / "sessions"
        self.exports_dir = self.base_dir / "exports"
        self.logs_dir = self.base_dir / "logs"
        self.batches_dir = self.base_dir / "batches"
        for path in (self.sessions_dir, self.exports_dir, self.logs_dir, self.batches_dir):
            path.mkdir(parents=True, exist_ok=True)
        self.active_batch_pointer = self.batches_dir / "_active.json"

    def session_dir(self, session_id: str) -> Path:
        return self.sessions_dir / session_id

    def save_session(self, session: Session) -> None:
        path = self.session_dir(session.session_id)
        path.mkdir(parents=True, exist_ok=True)
        summary = final_summary(session)
        session.final_summary = summary
        advanced = compute_advanced_metrics(session)
        self._write_json(path / "session.json", session.to_dict())
        self._write_json(path / "summary.json", {**summary, "advanced_metrics": advanced})
        self._write_json(path / "raw_events.json", self._raw_payload(session))
        self._write_task_csvs(session)

    def load_session(self, session_id: str) -> Session:
        path = self.session_dir(session_id) / "session.json"
        if not path.exists():
            raise FileNotFoundError(f"Missing session file: {path}")
        with path.open("r", encoding="utf-8") as file:
            return Session.from_dict(json.load(file))

    def list_sessions(self) -> list[Session]:
        sessions: list[Session] = []
        for session_file in sorted(self.sessions_dir.glob("*/session.json"), reverse=True):
            try:
                with session_file.open("r", encoding="utf-8") as file:
                    sessions.append(Session.from_dict(json.load(file)))
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                continue
        return sessions

    def export_json(self, session: Session) -> Path:
        self.save_session(session)
        output = self.exports_dir / f"{session.session_id}_raw_session.json"
        shutil.copy2(self.session_dir(session.session_id) / "session.json", output)
        return output

    def export_summary_csv(self, session: Session) -> Path:
        self.save_session(session)
        output = self.exports_dir / f"{session.session_id}_summary.csv"
        summary = final_summary(session)
        row: dict[str, Any] = {
            "session_id": session.session_id,
            "participant_name": session.participant_name,
            "input_method": session.input_method,
            "seed": session.seed,
            "screen_width": session.screen_width,
            "screen_height": session.screen_height,
            "started_at": session.started_at,
            "completed_at": session.completed_at or "",
            **summary,
        }
        for task_id, result in session.task_results.items():
            row[f"{task_id}_status"] = result.status
            row[f"{task_id}_score"] = result.score
        advanced = compute_advanced_metrics(session)
        for task_id, task_adv in advanced.items():
            for key, value in task_adv.items():
                row[f"{task_id}_adv_{key}"] = value
        with output.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(row.keys()))
            writer.writeheader()
            writer.writerow(row)
        return output

    def export_all_sessions_csv(self) -> Path:
        sessions = self.list_sessions()
        if not sessions:
            raise ValueError("No sessions to export")
        output = self.exports_dir / "all_sessions_summary.csv"
        rows: list[dict[str, Any]] = []
        for session in sessions:
            summary = final_summary(session)
            advanced = compute_advanced_metrics(session)
            row: dict[str, Any] = {
                "session_id": session.session_id,
                "participant_name": session.participant_name,
                "input_method": session.input_method,
                "seed": session.seed,
                "screen_width": session.screen_width,
                "screen_height": session.screen_height,
                "started_at": session.started_at,
                "completed_at": session.completed_at or "",
                **summary,
            }
            for task_id, result in session.task_results.items():
                row[f"{task_id}_status"] = result.status
                row[f"{task_id}_score"] = result.score
            for task_id, task_adv in advanced.items():
                for key, value in task_adv.items():
                    row[f"{task_id}_adv_{key}"] = value
            rows.append(row)
        self._write_csv(output, rows)
        return output

    def export_simple_csv(self, sessions: list[Session], filename: str | None = None) -> Path:
        if not sessions:
            raise ValueError("No sessions to export")
        if filename is None:
            filename = (
                f"{sessions[0].session_id}_simple.csv"
                if len(sessions) == 1
                else "sessions_simple.csv"
            )
        desktop = Path.home() / "Desktop"
        desktop.mkdir(parents=True, exist_ok=True)
        output = desktop / filename
        rows: list[dict[str, Any]] = []
        for session in sessions:
            row: dict[str, Any] = {
                "session_id": session.session_id,
                "movement_score": session.task_results["movement"].score if "movement" in session.task_results else "",
                "accuracy_score": session.task_results["accuracy"].score if "accuracy" in session.task_results else "",
                "tracking_score": session.task_results["tracking"].score if "tracking" in session.task_results else "",
                "clicking_score": session.task_results["clicking"].score if "clicking" in session.task_results else "",
            }
            for key, value in session.tags.items():
                row[f"tag:{key}"] = value
            rows.append(row)
        self._write_csv(output, rows)
        return output

    def _write_task_csvs(self, session: Session) -> None:
        path = self.session_dir(session.session_id)
        filenames = {
            "movement": "movement_trials.csv",
            "accuracy": "accuracy_trials.csv",
            "tracking": "tracking_samples.csv",
            "clicking": "clicking_trials.csv",
        }
        for task_id, filename in filenames.items():
            result = session.task_results.get(task_id)
            if not result:
                continue
            self._write_csv(path / filename, result.raw)

    @property
    def theme_pointer(self) -> Path:
        return self.base_dir / "theme.json"

    def get_theme(self) -> str:
        if not self.theme_pointer.exists():
            return "light"
        try:
            with self.theme_pointer.open("r", encoding="utf-8") as file:
                payload = json.load(file)
            name = payload.get("theme", "light")
            return name if name in {"light", "dark"} else "light"
        except (OSError, json.JSONDecodeError):
            return "light"

    def set_theme(self, name: str) -> None:
        if name not in {"light", "dark"}:
            name = "light"
        self._write_json(self.theme_pointer, {"theme": name})

    def _batch_path(self, batch_id: str) -> Path:
        return self.batches_dir / f"{batch_id}.json"

    def save_batch(self, batch: Batch) -> None:
        self._write_json(self._batch_path(batch.batch_id), batch.to_dict())

    def load_batch(self, batch_id: str) -> Batch:
        path = self._batch_path(batch_id)
        if not path.exists():
            raise FileNotFoundError(f"Missing batch file: {path}")
        with path.open("r", encoding="utf-8") as file:
            return Batch.from_dict(json.load(file))

    def list_batches(self) -> list[Batch]:
        batches: list[Batch] = []
        for batch_file in self.batches_dir.glob("batch_*.json"):
            try:
                with batch_file.open("r", encoding="utf-8") as file:
                    batches.append(Batch.from_dict(json.load(file)))
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                continue
        batches.sort(key=lambda b: b.started_at, reverse=True)
        return batches

    def get_active_batch(self) -> Batch | None:
        if not self.active_batch_pointer.exists():
            return None
        try:
            with self.active_batch_pointer.open("r", encoding="utf-8") as file:
                payload = json.load(file)
            batch_id = payload.get("batch_id")
            if not batch_id:
                return None
            batch = self.load_batch(batch_id)
        except (OSError, json.JSONDecodeError, FileNotFoundError):
            return None
        return batch if batch.is_active() else None

    def start_batch(self, name: str, target_session_count: int = 0) -> Batch:
        existing = self.get_active_batch()
        if existing is not None:
            raise ValueError(f"A batch is already active: {existing.name}")
        batch = Batch.create(name, target_session_count=target_session_count)
        self.save_batch(batch)
        self._write_json(self.active_batch_pointer, {"batch_id": batch.batch_id})
        return batch

    def remove_session_from_batch(self, batch_id: str, session_id: str) -> None:
        batch = self.load_batch(batch_id)
        if session_id not in batch.session_ids:
            return
        batch.session_ids.remove(session_id)
        self.save_batch(batch)

    def end_active_batch(self) -> Batch | None:
        batch = self.get_active_batch()
        if batch is None:
            return None
        batch.ended_at = utcish_now()
        self.save_batch(batch)
        try:
            self.active_batch_pointer.unlink()
        except FileNotFoundError:
            pass
        return batch

    def add_session_to_active_batch(self, session: Session) -> None:
        batch = self.get_active_batch()
        if batch is None:
            return
        if session.session_id in batch.session_ids:
            return
        session.batch_id = batch.batch_id
        batch.session_ids.append(session.session_id)
        self.save_batch(batch)

    def export_batch_csv(self, batch_id: str) -> Path:
        batch = self.load_batch(batch_id)
        if not batch.session_ids:
            raise ValueError(f"Batch '{batch.name}' has no sessions to export.")
        rows: list[dict[str, Any]] = []
        for session_id in batch.session_ids:
            try:
                session = self.load_session(session_id)
            except (OSError, FileNotFoundError, ValueError):
                continue
            if session.status == "aborted":
                continue
            summary = final_summary(session)
            advanced = compute_advanced_metrics(session)
            row: dict[str, Any] = {
                "batch_id": batch.batch_id,
                "batch_name": batch.name,
                "session_id": session.session_id,
                "participant_name": session.participant_name,
                "input_method": session.input_method,
                "seed": session.seed,
                "screen_width": session.screen_width,
                "screen_height": session.screen_height,
                "started_at": session.started_at,
                "completed_at": session.completed_at or "",
                **summary,
            }
            for task_id, result in session.task_results.items():
                row[f"{task_id}_status"] = result.status
                row[f"{task_id}_score"] = result.score
            for task_id, task_adv in advanced.items():
                for key, value in task_adv.items():
                    row[f"{task_id}_adv_{key}"] = value
            rows.append(row)
        if not rows:
            raise ValueError(f"Batch '{batch.name}' has no readable sessions.")
        output = self.exports_dir / f"{batch.batch_id}_summary.csv"
        self._write_csv(output, rows)
        return output

    @staticmethod
    def _raw_payload(session: Session) -> dict[str, Any]:
        return {
            "session_id": session.session_id,
            "tasks": {
                task_id: {
                    "summary": result.summary,
                    "raw": result.raw,
                }
                for task_id, result in session.task_results.items()
            },
        }

    @staticmethod
    def _write_json(path: Path, data: dict[str, Any]) -> None:
        with path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)

    @staticmethod
    def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        fields: list[str] = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

