from datetime import datetime

from core.models import ExecutionResult
from core.settings import LOGS_DIR
from core.execution_repository import (
    ExecutionRepository,
    JsonExecutionRepository,
    SQLiteExecutionRepository,
)
from core.settings import DATABASE_PATH, LOGS_DIR


class ExecutionLogger:

    LOG_FOLDER = LOGS_DIR
    _repository: ExecutionRepository | None = None

    @classmethod
    def set_repository(cls, repository: ExecutionRepository) -> None:
        cls._repository = repository

    @classmethod
    def _get_repository(cls) -> ExecutionRepository:
        if cls._repository is None:
            cls._repository = SQLiteExecutionRepository(
                DATABASE_PATH,
                legacy_logs_folder=cls.LOG_FOLDER,
            )
        return cls._repository

    @classmethod
    def ensure_folder(cls) -> None:

        cls.LOG_FOLDER.mkdir(
            parents=True,
            exist_ok=True
        )

    @classmethod
    def save(
        cls,
        payload: ExecutionResult | dict,
    ) -> None:

        if isinstance(
            payload,
            ExecutionResult,
        ):
            payload = payload.model_dump(
                mode="json"
            )

        cls._get_repository().save(payload)

    @classmethod
    def create_execution_id(
        cls
    ) -> str:

        return datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )