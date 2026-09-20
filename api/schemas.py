from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class HealthDetailResponse(BaseModel):
    status: str
    python: dict
    manifests: dict
    sqlite: dict
    projects: list[dict]
    outputs: list[dict]
    permissions: list[dict]
    problems: list[str]


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
    project_id: str | None = None
    status: str
    duration_seconds: float | None = None
    started_at: str | None = None
    finished_at: str | None = None
    error_message: str | None = None
    uploaded_files: list[str] = []
    outputs: list[str] = []


class CreateExecutionRequest(BaseModel):
    project_id: str


class CreateExecutionResponse(BaseModel):
    execution_id: str
    status: str


class ExecutionFilesResponse(BaseModel):
    execution_id: str
    status: str
    uploaded_files: list[str]


class ErrorResponse(BaseModel):
    detail: str