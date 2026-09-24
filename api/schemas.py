from pydantic import BaseModel
from typing import Any

from core.models import ExecutionPlan


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
    outputs: list[str] = []


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


class AIAnalyzeResponse(BaseModel):
    diagnostic: str
    viability: str
    inputs: list[dict[str, Any]]
    outputs: list[str]
    complexity: str
    project_id: str | None = None
    project_name: str | None = None
    category: str | None = None
    pattern: str | None = None
    steps: list[dict[str, Any]] = []
    manifest_data: dict[str, Any] = {}
    understanding: dict[str, Any] = {}
    pipeline_validation: dict[str, Any] = {}
    execution_plan: dict[str, Any] | ExecutionPlan = {}


class AIManifestResponse(BaseModel):
    manifest: str


class AICreateProjectResponse(BaseModel):
    project_id: str
    project_path: str
    manifest_path: str
    readme_path: str
    entrypoint_path: str
    published_manifest_path: str | None = None
    status: str


class AICreateProjectRequest(BaseModel):
    prompt: str
    manifest_data: dict[str, Any] | None = None
    approved: bool = False