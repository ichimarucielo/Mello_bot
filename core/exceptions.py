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
class MelloBotException(Exception):
    """Base exception for MELLO BOT"""
    pass

class ProjectNotFoundError(MelloBotException):
    """Raised when a project is not found"""
    pass

class FileProcessingError(MelloBotException):
    """Raised when there's an error processing a file"""
    pass

class ValidationError(MelloBotException):
    """Raised when validation fails"""
    pass

class ExecutionError(MelloBotException):
    """Raised when execution fails"""
    pass
