from core.execution_repository import SQLiteExecutionRepository
from core.settings import DATABASE_PATH


class AutomationRequestService:
    @staticmethod
    def create(
        sharepoint_id: int,
        title: str,
        request: str,
        complexity: str | None,
        suggested_project_id: str | None,
    ) -> None:
        SQLiteExecutionRepository(DATABASE_PATH).save_automation_request(
            sharepoint_id=sharepoint_id,
            title=title,
            request=request,
            complexity=complexity,
            suggested_project_id=suggested_project_id,
        )

    @staticmethod
    def list() -> list[dict]:
        from core.settings import DATABASE_PATH

        print("DATABASE_PATH =", DATABASE_PATH)
        return SQLiteExecutionRepository(DATABASE_PATH).list_automation_requests()