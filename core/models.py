from datetime import datetime
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
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

    steps: list["OperationStep"] = Field(default_factory=list)

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


class OperationStep(BaseModel):
    operation: str

    description: str = ""

    parameters: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_step(cls, value: Any) -> Any:
        if not isinstance(value, dict) or "operation" in value:
            return value
        operation = value.get("type")
        if not operation:
            return value
        parameters = {
            key: item
            for key, item in value.items()
            if key not in {"type", "description"}
        }
        if operation in {"join", "reconcile"} and "key" not in parameters:
            parameters["key"] = parameters.get("left_key") or parameters.get(
                "right_key"
            )
        return {
            "operation": operation,
            "description": value.get("description", ""),
            "parameters": parameters,
        }

    @property
    def condition(self) -> str | None:
        return self.parameters.get("condition")

    @property
    def formula(self) -> str | None:
        return self.parameters.get("formula")

    @property
    def group_by(self) -> str | list[str] | None:
        return self.parameters.get("group_by")

    @property
    def columns(self) -> list[str] | None:
        return self.parameters.get("columns")

    @property
    def mapping(self) -> dict[str, str] | None:
        return self.parameters.get("mapping")

    @property
    def key(self) -> str | None:
        return self.parameters.get("key")

    def __getitem__(self, key: str) -> Any:
        if key == "type":
            return self.operation
        if key in type(self).model_fields:
            return getattr(self, key)
        return self.parameters[key]

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, dict):
            legacy = {"type": self.operation, **self.parameters}
            return all(legacy.get(key) == value for key, value in other.items())
        return super().__eq__(other)


class ExecutionPlan(BaseModel):
    summary: str

    documents: list[dict[str, Any]] = Field(default_factory=list)

    transformations: list[dict[str, Any]] = Field(default_factory=list)

    outputs: list[str] = Field(default_factory=list)

    approved: bool = False

    @property
    def detected_documents(self) -> list[dict[str, Any]]:
        return self.documents

    @property
    def detected_operations(self) -> list[dict[str, Any]]:
        return self.transformations


class AutomationAnalysis(BaseModel):
    diagnostic: str

    viability: str

    inputs: list[dict[str, Any]] = Field(default_factory=list)

    outputs: list[str] = Field(default_factory=list)

    steps: list[OperationStep] = Field(default_factory=list)

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

    execution_plan: ExecutionPlan | None = None


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