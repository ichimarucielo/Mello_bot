from datetime import datetime
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from core.enums import ExecutionStatus


class EntryPoint(BaseModel):
    script: str


class RequiredFile(BaseModel):
    id: str

    display_name: str

    accepted_extensions: list[str]

    critical_columns: list[str] = Field(default_factory=list)

    required_columns: list[str]

    cli_argument: str | None = None


class Manifest(BaseModel):

    model_config = ConfigDict(
        extra="allow"
    )

    id: str

    name: str

    category: str

    description: str

    project_path: str

    timeout_seconds: int = Field(
        default=1800,
        ge=1,
        description="Timeout em segundos para a execução do ETL.",
    )

    entrypoint: EntryPoint

    required_files: list[RequiredFile]

    steps: list[dict[str, Any]] = Field(default_factory=list)

    outputs: list[str]

    tags: list[str] = Field(
        default_factory=list
    )


class ExecutionContext(BaseModel):
    execution_id: str

    project_id: str

    started_at: datetime

    status: ExecutionStatus = (
        ExecutionStatus.PENDING
    )

    uploaded_files: list[str] = Field(
        default_factory=list
    )


class ExecutionResult(BaseModel):
    execution_id: str

    project_id: str

    status: ExecutionStatus

    duration_seconds: float

    started_at: datetime | None = None

    finished_at: datetime | None = None

    outputs: list[str] = Field(
        default_factory=list
    )

    error_message: str | None = None

    user: str = "Usuário Local"

    uploaded_files: list[str] = Field(default_factory=list)


class RunProjectResult(BaseModel):
    status: str

    mapped_files: list[str]

    outputs: list[str]


class AutomationRequest(BaseModel):
    prompt: str = Field(min_length=1)


class AutomationAnalysis(BaseModel):
    diagnostic: str

    viability: str

    inputs: list[dict[str, Any]] = Field(default_factory=list)

    outputs: list[str] = Field(default_factory=list)

    steps: list[dict[str, Any]] = Field(default_factory=list)

    complexity: str

    pattern: str = "generic"

    project_id: str

    project_name: str

    category: str

    description: str

    project_path: str

    entrypoint: str

    timeout_seconds: int = Field(default=1800, ge=1)

    manifest_data: dict = Field(default_factory=dict)

    understanding: dict[str, Any] = Field(default_factory=dict)

    pipeline_validation: dict[str, Any] = Field(default_factory=dict)


class AutomationGenerationResult(BaseModel):
    project_id: str

    project_path: str

    manifest_path: str

    readme_path: str

    entrypoint_path: str

    published_manifest_path: str | None = None

    status: str

    analysis: AutomationAnalysis

class HistoryEntry(BaseModel):
    execution_id: str

    project_id: str

    status: ExecutionStatus

    duration_seconds: float

    started_at: datetime | None = None

    finished_at: datetime | None = None

    error_message: str | None = None