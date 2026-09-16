from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from core.enums import ExecutionStatus
from core.execution_logger import ExecutionLogger
from core.history_service import HistoryService
from core.orchestrator import Orchestrator
from core.settings import INPUTS_DIR


@dataclass
class StagedUpload:
    name: str
    content: bytes


class ExecutionService:
    STAGING_FOLDER = ".executions"

    @classmethod
    def create(cls, project_id: str) -> dict:
        project = Orchestrator.get_project(project_id)
        execution_id = ExecutionLogger.create_execution_id()
        payload = {
            "execution_id": execution_id,
            "project_id": project.id,
            "status": ExecutionStatus.PENDING.value,
            "duration_seconds": 0.0,
            "started_at": datetime.now().isoformat(),
            "finished_at": None,
            "outputs": [],
            "uploaded_files": [],
            "error_message": None,
            "user": "Usuário Local",
        }
        ExecutionLogger.save(payload)
        return payload

    @classmethod
    def stage_files(
        cls,
        execution_id: str,
        files: Iterable[StagedUpload],
    ) -> list[str]:
        execution = HistoryService.get_execution(execution_id)
        if execution is None:
            raise KeyError(execution_id)

        folder = cls._staging_folder(execution)
        folder.mkdir(parents=True, exist_ok=True)
        names = []
        for uploaded_file in files:
            safe_name = Path(uploaded_file.name).name
            if not safe_name or safe_name in {".", ".."}:
                continue
            (folder / safe_name).write_bytes(uploaded_file.content)
            names.append(safe_name)

        execution["uploaded_files"] = names
        ExecutionLogger.save(execution)
        return names

    @classmethod
    def run(cls, execution_id: str) -> None:
        execution = HistoryService.get_execution(execution_id)
        if execution is None:
            return

        execution["status"] = ExecutionStatus.RUNNING.value
        ExecutionLogger.save(execution)
        uploaded_files = [
            StagedUpload(
                name=path.name,
                content=path.read_bytes(),
            )
            for path in cls._staging_folder(execution).glob("*")
            if path.is_file()
        ]

        try:
            Orchestrator.run_project(
                project_id=execution["project_id"],
                uploaded_files=uploaded_files,
                execution_id=execution_id,
            )
        except Exception as error:
            current = HistoryService.get_execution(execution_id) or execution
            if current.get("status") != ExecutionStatus.FAILED.value:
                now = datetime.now().isoformat()
                current.update(
                    {
                        "status": ExecutionStatus.FAILED.value,
                        "finished_at": now,
                        "error_message": str(error),
                    }
                )
                ExecutionLogger.save(current)

    @classmethod
    def _staging_folder(cls, execution: dict) -> Path:
        return (
            INPUTS_DIR
            / execution["project_id"]
            / cls.STAGING_FOLDER
            / execution["execution_id"]
        )
