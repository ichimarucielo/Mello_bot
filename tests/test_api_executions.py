import asyncio
from io import BytesIO

from fastapi import BackgroundTasks, UploadFile

from api.app import (
    create_execution,
    get_execution_details,
    list_executions,
    upload_execution_files,
)
from api.schemas import CreateExecutionRequest
from core.enums import ExecutionStatus
from core.execution_logger import ExecutionLogger
from core.execution_repository import SQLiteExecutionRepository
from core.history_service import HistoryService
from core.models import ExecutionResult


class ProjectStub:
    id = "demo"


def test_execution_api_creates_uploads_and_exposes_history(tmp_path, monkeypatch):
    repository = SQLiteExecutionRepository(tmp_path / "mello.db")
    ExecutionLogger.set_repository(repository)
    HistoryService.set_repository(repository)
    monkeypatch.setattr("api.app.Orchestrator.get_project", lambda project_id: ProjectStub())

    def fake_run_project(**kwargs):
        ExecutionLogger.save(
            ExecutionResult(
                execution_id=kwargs["execution_id"],
                project_id=kwargs["project_id"],
                status=ExecutionStatus.SUCCESS,
                duration_seconds=0.2,
                uploaded_files=["input.csv"],
                outputs=["result.xlsx"],
            )
        )

    monkeypatch.setattr("api.app.Orchestrator.run_project", fake_run_project)
    created = create_execution(CreateExecutionRequest(project_id="demo"))
    execution_id = created["execution_id"]
    background_tasks = BackgroundTasks()
    uploaded = asyncio.run(
        upload_execution_files(
            execution_id=execution_id,
            background_tasks=background_tasks,
            files=[
                UploadFile(
                    filename="input.csv",
                    file=BytesIO(b"a;b\n1;2\n"),
                )
            ],
        )
    )
    assert uploaded["uploaded_files"] == ["input.csv"]
    asyncio.run(background_tasks())

    details = get_execution_details(execution_id)
    assert details["status"] == "success"
    assert len(list_executions()) == 1
