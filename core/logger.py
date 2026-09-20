import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("mello_bot")
logger.setLevel(logging.INFO)
logger.propagate = False

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)


def _normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    for key in [
        "uploaded_files",
        "outputs",
    ]:
        if key in normalized and normalized[key] is None:
            normalized[key] = []
    if "status" not in normalized:
        normalized["status"] = "unknown"
    if "duration" not in normalized:
        normalized["duration"] = 0
    if "exception" not in normalized:
        normalized["exception"] = None
    if "execution_id" not in normalized:
        normalized["execution_id"] = None
    if "project_id" not in normalized:
        normalized["project_id"] = None
    return normalized


def _emit(event: str, **payload: Any) -> None:
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
    }
    record.update(_normalize_payload(payload))
    logger.info(json.dumps(record, ensure_ascii=False, default=str))


def log_execution_start(
    *,
    execution_id: str | None,
    project_id: str | None,
    duration: float | None = None,
    uploaded_files: list[str] | None = None,
    status: str = "running",
    **extra: Any,
) -> None:
    _emit(
        "execution_start",
        execution_id=execution_id,
        project_id=project_id,
        duration=duration or 0,
        uploaded_files=uploaded_files or [],
        status=status,
        **extra,
    )


def log_execution_success(
    *,
    execution_id: str | None,
    project_id: str | None,
    duration: float | None = None,
    uploaded_files: list[str] | None = None,
    outputs: list[str] | None = None,
    status: str = "success",
    **extra: Any,
) -> None:
    _emit(
        "execution_success",
        execution_id=execution_id,
        project_id=project_id,
        duration=duration or 0,
        uploaded_files=uploaded_files or [],
        outputs=outputs or [],
        status=status,
        **extra,
    )


def log_execution_failure(
    *,
    execution_id: str | None,
    project_id: str | None,
    duration: float | None = None,
    uploaded_files: list[str] | None = None,
    outputs: list[str] | None = None,
    exception: Exception | str | None = None,
    status: str = "failed",
    **extra: Any,
) -> None:
    _emit(
        "execution_failure",
        execution_id=execution_id,
        project_id=project_id,
        duration=duration or 0,
        uploaded_files=uploaded_files or [],
        outputs=outputs or [],
        exception=str(exception) if exception is not None else None,
        status=status,
        **extra,
    )
