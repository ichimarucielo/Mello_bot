class ProjectNotFoundError(Exception):
    pass


class TimeoutExecutionError(RuntimeError):
    """Raised when an ETL execution exceeds the configured timeout."""

    def __init__(self, project_id: str, timeout_seconds: int):
        self.project_id = project_id
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"Execução do projeto '{project_id}' excedeu o timeout de {timeout_seconds} segundos."
        )
