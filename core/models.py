from datetime import datetime
from pydantic import BaseModel, Field
from typing import List

from core.enums import ExecutionStatus


class EntryPoint(BaseModel):
    script: str


class RequiredFile(BaseModel):
    id: str
    display_name: str

    accepted_extensions: List[str]

    required_columns: List[str]


class Manifest(BaseModel):
    id: str

    name: str

    category: str

    description: str

    project_path: str

    entrypoint: EntryPoint

    required_files: List[RequiredFile]

    outputs: List[str]


class ExecutionContext(BaseModel):
    execution_id: str

    project_id: str

    started_at: datetime

    status: ExecutionStatus = ExecutionStatus.PENDING

    uploaded_files: List[str] = Field(default_factory=list)


class ExecutionResult(BaseModel):
    execution_id: str

    status: ExecutionStatus

    duration_seconds: float

    outputs: List[str] = Field(default_factory=list)

    error_message: str | None = None