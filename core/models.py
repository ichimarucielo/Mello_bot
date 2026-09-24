from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
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

    pipeline: "PipelineDefinition | None" = None

    outputs: list[str]

    tags: list[str] = Field(
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

    manifest_data: dict[str, Any] | None = None


class OperationStep(BaseModel):
    operation: str

    description: str = ""

    parameters: dict[str, Any] = Field(default_factory=dict)

    confidence: str = "baixa"

    pending_confirmation: list[str] = Field(default_factory=list)

    @field_validator("confidence", mode="before")
    @classmethod
    def default_null_confidence(cls, value: Any) -> str:
        return value or "baixa"

    @field_validator("pending_confirmation", mode="before")
    @classmethod
    def default_null_pending_confirmation(cls, value: Any) -> list[str]:
        return value or []

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_step(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        if "operation" in value:
            normalized = dict(value)
            parameters = normalized.get("parameters") or {}
            pending = normalized.get("pending_confirmation") or []
            has_evidence = any(item is not None for item in parameters.values())
            default_confidence = "baixa" if pending or not has_evidence else "alta"
            normalized["description"] = normalized.get("description") or ""
            normalized["parameters"] = parameters
            normalized["confidence"] = (
                normalized.get("confidence") or default_confidence
            )
            normalized["pending_confirmation"] = pending
            return normalized
        operation = value.get("type")
        if not operation:
            return value
        parameters = {
            key: item
            for key, item in value.items()
            if key not in {
                "type",
                "description",
                "confidence",
                "pending_confirmation",
            }
        }
        if operation in {"join", "reconcile"} and "key" not in parameters:
            parameters["key"] = parameters.get("left_key") or parameters.get(
                "right_key"
            )
        pending = value.get("pending_confirmation") or []
        has_evidence = any(item is not None for item in parameters.values())
        default_confidence = "baixa" if pending or not has_evidence else "alta"
        return {
            "operation": operation,
            "description": value.get("description", ""),
            "parameters": parameters,
            "confidence": value.get("confidence") or default_confidence,
            "pending_confirmation": pending,
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
            legacy = {
                "type": self.operation,
                **self.parameters,
                "confidence": self.confidence,
                "pending_confirmation": self.pending_confirmation,
            }
            return all(legacy.get(key) == value for key, value in other.items())
        return super().__eq__(other)


class PipelineDefinition(BaseModel):
    """V2 declarative pipeline while preserving the legacy ``steps`` field."""

    operations: list[OperationStep] = Field(default_factory=list)

    @classmethod
    def from_manifest(cls, manifest: Manifest) -> "PipelineDefinition":
        if manifest.pipeline and manifest.pipeline.operations:
            return manifest.pipeline
        return cls(operations=list(manifest.steps))


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

    manifest: Manifest | None = None

    inputs: dict[str, str] = Field(default_factory=dict)

    storage_provider: str = "local"

    working_directory: str | None = None

    logger_name: str = "mello_bot"


class ExecutionPlan(BaseModel):
    summary: str

    intent: str = "Intenção não identificada"

    intent_confidence: str = "baixa"

    intent_source: list[str] = Field(default_factory=list)

    intent_summary: str = "O MELLO preparou um plano com base nas informações disponíveis."

    decisions: list[dict[str, Any]] = Field(default_factory=list)

    documents: list[dict[str, Any]] = Field(default_factory=list)

    transformations: list[dict[str, Any]] = Field(default_factory=list)

    profiles: list[dict[str, Any]] = Field(default_factory=list)

    keys: list[str] = Field(default_factory=list)

    risks: list[str] = Field(default_factory=list)

    open_questions: list[str] = Field(default_factory=list)

    outputs: list[str] = Field(default_factory=list)

    output_details: list[dict[str, Any]] = Field(default_factory=list)

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


Manifest.model_rebuild()