from datetime import datetime

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

    entrypoint: EntryPoint

    required_files: list[RequiredFile]

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

class HistoryEntry(BaseModel):
    execution_id: str

    project_id: str

    status: ExecutionStatus

    duration_seconds: float

    started_at: datetime | None = None

    finished_at: datetime | None = None

    error_message: str | None = None