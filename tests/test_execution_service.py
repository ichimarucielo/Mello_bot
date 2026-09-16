from core.enums import ExecutionStatus
from core.execution_logger import ExecutionLogger
from core.execution_repository import SQLiteExecutionRepository
from core.execution_service import ExecutionService, StagedUpload
from core.history_service import HistoryService
from core.models import ExecutionResult


class ProjectStub:
    id = "demo"


def test_execution_lifecycle_updates_state_and_stages_files(tmp_path, monkeypatch):
    repository = SQLiteExecutionRepository(tmp_path / "mello.db")
    ExecutionLogger.set_repository(repository)
    HistoryService.set_repository(repository)
    monkeypatch.setattr("core.execution_service.INPUTS_DIR", tmp_path / "inputs")
    monkeypatch.setattr(
        "core.execution_service.Orchestrator.get_project",
        lambda project_id: ProjectStub(),
    )

    execution = ExecutionService.create("demo")
    execution_id = execution["execution_id"]
    uploaded_files = ExecutionService.stage_files(
        execution_id,
        [StagedUpload(name="input.csv", content=b"a;b\n1;2\n")],
    )

    assert execution["status"] == ExecutionStatus.PENDING.value
    assert uploaded_files == ["input.csv"]

    def fake_run_project(**kwargs):
        ExecutionLogger.save(
            ExecutionResult(
                execution_id=kwargs["execution_id"],
                project_id=kwargs["project_id"],
                status=ExecutionStatus.SUCCESS,
                duration_seconds=0.1,
                uploaded_files=["input.csv"],
            )
        )

    monkeypatch.setattr(
        "core.execution_service.Orchestrator.run_project",
        fake_run_project,
    )
    ExecutionService.run(execution_id)

    assert HistoryService.get_execution(execution_id)["status"] == "success"
