import json

from core.execution_repository import (
    JsonExecutionRepository,
    SQLiteExecutionRepository,
)


def _payload(execution_id: str, started_at: str) -> dict:
    return {
        "execution_id": execution_id,
        "project_id": "demo",
        "status": "success",
        "started_at": started_at,
        "duration_seconds": 1.0,
    }


def test_sqlite_repository_persists_and_orders_executions(tmp_path):
    repository = SQLiteExecutionRepository(tmp_path / "executions.db")
    older = _payload("older", "2026-09-01T10:00:00")
    newer = _payload("newer", "2026-09-02T10:00:00")
    older["uploaded_files"] = ["older.csv"]
    newer["outputs"] = ["result.xlsx"]
    repository.save(older)
    repository.save(newer)

    assert [item["execution_id"] for item in repository.list()] == [
        "newer",
        "older",
    ]
    assert repository.list()[0]["outputs"] == ["result.xlsx"]
    assert repository.list()[1]["uploaded_files"] == ["older.csv"]


def test_sqlite_repository_migrates_json_logs(tmp_path):
    legacy_folder = tmp_path / "logs"
    legacy_folder.mkdir()
    payload = _payload("legacy", "2026-09-03T10:00:00")
    payload["uploaded_files"] = ["input.csv"]
    (legacy_folder / "legacy.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    repository = SQLiteExecutionRepository(
        tmp_path / "storage" / "mello.db",
        legacy_logs_folder=legacy_folder,
    )

    assert repository.list() == [payload]


def test_json_repository_keeps_existing_file_contract(tmp_path):
    repository = JsonExecutionRepository(tmp_path)
    payload = _payload("exec-json", "2026-09-02T10:00:00")

    repository.save(payload)

    assert repository.list() == [payload]