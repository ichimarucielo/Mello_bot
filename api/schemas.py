from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class ProjectResponse(BaseModel):
    id: str
    name: str
    category: str | None = None
    description: str | None = None


class OutputResponse(BaseModel):
    name: str
    size_bytes: int


class RunResponse(BaseModel):
    status: str
    mapped_files: list[str]
    outputs: list[str]


class ExecuteResponse(BaseModel):
    status: str
    project_id: str
    files: dict[str, str]


class HistoryResponse(BaseModel):
    execution_id: str
    status: str
    duration_seconds: float | None = None


class ErrorResponse(BaseModel):
    detail: str