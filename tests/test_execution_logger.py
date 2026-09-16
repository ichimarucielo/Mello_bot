import json

from core.enums import ExecutionStatus
from core.execution_logger import ExecutionLogger
from core.execution_repository import JsonExecutionRepository
from core.models import ExecutionResult


def test_save_execution_result_writes_standard_observability_fields(tmp_path):
    ExecutionLogger.set_repository(JsonExecutionRepository(tmp_path))
    result = ExecutionResult(
        execution_id="exec-123",
        project_id="ia_quarteto",
        status=ExecutionStatus.SUCCESS,
        duration_seconds=5.3,
    )

    ExecutionLogger.save(result)

    payload = json.loads((tmp_path / "exec-123.json").read_text(encoding="utf-8"))
    assert payload["execution_id"] == "exec-123"
    assert payload["project_id"] == "ia_quarteto"
    assert payload["status"] == "success"
    assert payload["duration_seconds"] == 5.3
    assert "started_at" in payload
    assert "finished_at" in payload


def test_save_accepts_dictionary_payload(tmp_path):
    ExecutionLogger.set_repository(JsonExecutionRepository(tmp_path))
    payload = {
        "execution_id": "exec-dict",
        "project_id": "demo",
        "status": "success",
        "started_at": "2026-09-02T10:00:00",
        "finished_at": "2026-09-02T10:00:05",
        "duration_seconds": 5.0,
    }

    ExecutionLogger.save(payload)

    saved = json.loads((tmp_path / "exec-dict.json").read_text(encoding="utf-8"))
    assert saved == payload


def test_create_execution_id_has_expected_format():
    execution_id = ExecutionLogger.create_execution_id()

    assert len(execution_id) == 15
    assert execution_id[8] == "_"
