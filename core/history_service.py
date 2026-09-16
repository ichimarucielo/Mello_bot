from core.execution_repository import (
    ExecutionRepository,
    JsonExecutionRepository,
    SQLiteExecutionRepository,
)
from core.settings import DATABASE_PATH, LOGS_DIR


class HistoryService:

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
    def get_history(
        cls,
        limit: int = 10
    ) -> list:

        return cls._get_repository().list(limit)

    @classmethod
    def get_execution(cls, execution_id: str) -> dict | None:
        return cls._get_repository().get(execution_id)