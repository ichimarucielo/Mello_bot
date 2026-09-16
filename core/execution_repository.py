import json
import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


ExecutionPayload = dict[str, Any]


class ExecutionRepository(ABC):
    @abstractmethod
    def save(self, payload: ExecutionPayload) -> None:
        """Persists one execution payload."""

    @abstractmethod
    def list(self, limit: int = 10) -> list[ExecutionPayload]:
        """Returns executions ordered from newest to oldest."""

    @abstractmethod
    def get(self, execution_id: str) -> ExecutionPayload | None:
        """Returns one execution by ID."""


class JsonExecutionRepository(ExecutionRepository):
    def __init__(self, folder: Path):
        self.folder = Path(folder)

    def save(self, payload: ExecutionPayload) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        execution_id = payload["execution_id"]
        log_file = self.folder / f"{execution_id}.json"
        log_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=4),
            encoding="utf-8",
        )

    def list(self, limit: int = 10) -> list[ExecutionPayload]:
        if limit <= 0 or not self.folder.exists():
            return []

        executions = []
        for log_file in self.folder.glob("*.json"):
            try:
                executions.append(json.loads(log_file.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue

        executions.sort(
            key=lambda payload: payload.get(
                "started_at",
                payload.get("start_time", ""),
            ),
            reverse=True,
        )
        return executions[:limit]

    def get(self, execution_id: str) -> ExecutionPayload | None:
        for payload in self.list(limit=10000):
            if payload.get("execution_id") == execution_id:
                return payload
        return None


class SQLiteExecutionRepository(ExecutionRepository):
    def __init__(
        self,
        database_path: Path,
        legacy_logs_folder: Path | None = None,
    ):
        self.database_path = Path(database_path)
        self._ensure_schema()
        if legacy_logs_folder is not None:
            self.migrate_json_logs(legacy_logs_folder)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_schema(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY,
                    name TEXT,
                    category TEXT,
                    description TEXT,
                    project_path TEXT,
                    manifest_path TEXT
                );

                CREATE TABLE IF NOT EXISTS executions (
                    execution_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    duration_seconds REAL NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    error_message TEXT,
                    user_name TEXT,
                    payload TEXT NOT NULL,
                    FOREIGN KEY (project_id) REFERENCES projects(project_id)
                );

                CREATE TABLE IF NOT EXISTS execution_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    FOREIGN KEY (execution_id) REFERENCES executions(execution_id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS execution_outputs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id TEXT NOT NULL,
                    output_name TEXT NOT NULL,
                    FOREIGN KEY (execution_id) REFERENCES executions(execution_id)
                        ON DELETE CASCADE
                );
                """
            )

    def save(self, payload: ExecutionPayload) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO executions (
                    execution_id, project_id, status, duration_seconds,
                    started_at, finished_at, error_message, user_name, payload
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(execution_id) DO UPDATE SET
                    project_id = excluded.project_id,
                    status = excluded.status,
                    duration_seconds = excluded.duration_seconds,
                    started_at = excluded.started_at,
                    finished_at = excluded.finished_at,
                    error_message = excluded.error_message,
                    user_name = excluded.user_name,
                    payload = excluded.payload
                """,
                (
                    payload["execution_id"],
                    payload.get("project_id", ""),
                    payload.get("status", ""),
                    payload.get("duration_seconds", 0),
                    payload.get("started_at", payload.get("start_time", "")),
                    payload.get("finished_at", payload.get("end_time", "")),
                    payload.get("error_message"),
                    payload.get("user", payload.get("user_name", "")),
                    json.dumps(payload, ensure_ascii=False),
                ),
            )
            connection.execute(
                "DELETE FROM execution_files WHERE execution_id = ?",
                (payload["execution_id"],),
            )
            connection.execute(
                "DELETE FROM execution_outputs WHERE execution_id = ?",
                (payload["execution_id"],),
            )
            connection.executemany(
                "INSERT INTO execution_files (execution_id, file_name) VALUES (?, ?)",
                [
                    (payload["execution_id"], file_name)
                    for file_name in payload.get("uploaded_files", [])
                ],
            )
            connection.executemany(
                "INSERT INTO execution_outputs (execution_id, output_name) VALUES (?, ?)",
                [
                    (payload["execution_id"], output_name)
                    for output_name in payload.get("outputs", [])
                ],
            )

    def list(self, limit: int = 10) -> list[ExecutionPayload]:
        if limit <= 0:
            return []

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT execution_id, payload
                FROM executions
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

            executions = []
            for row in rows:
                payload = json.loads(row["payload"])
                if "uploaded_files" in payload:
                    payload["uploaded_files"] = [
                        item["file_name"]
                        for item in connection.execute(
                            "SELECT file_name FROM execution_files WHERE execution_id = ? ORDER BY id",
                            (row["execution_id"],),
                        ).fetchall()
                    ]
                if "outputs" in payload:
                    payload["outputs"] = [
                        item["output_name"]
                        for item in connection.execute(
                            "SELECT output_name FROM execution_outputs WHERE execution_id = ? ORDER BY id",
                            (row["execution_id"],),
                        ).fetchall()
                    ]
                executions.append(payload)

        return executions

    def get(self, execution_id: str) -> ExecutionPayload | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT execution_id, payload FROM executions WHERE execution_id = ?",
                (execution_id,),
            ).fetchone()

            if row is None:
                return None

            payload = json.loads(row["payload"])
            if "uploaded_files" in payload:
                payload["uploaded_files"] = [
                    item["file_name"]
                    for item in connection.execute(
                        "SELECT file_name FROM execution_files WHERE execution_id = ? ORDER BY id",
                        (execution_id,),
                    ).fetchall()
                ]
            if "outputs" in payload:
                payload["outputs"] = [
                    item["output_name"]
                    for item in connection.execute(
                        "SELECT output_name FROM execution_outputs WHERE execution_id = ? ORDER BY id",
                        (execution_id,),
                    ).fetchall()
                ]
            return payload

    def migrate_json_logs(self, folder: Path) -> int:
        folder = Path(folder)
        if not folder.exists():
            return 0

        migrated = 0
        for log_file in folder.glob("*.json"):
            try:
                payload = json.loads(log_file.read_text(encoding="utf-8"))
                if "execution_id" not in payload:
                    continue
                self.save(payload)
                migrated += 1
            except (OSError, ValueError, KeyError):
                continue
        return migrated