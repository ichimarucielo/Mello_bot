from typing import Any

from core.models import OperationStep
from core.pipeline_catalog import get_operation


class PipelineValidator:
    """Valida a coerência estrutural de um pipeline declarativo."""

    @classmethod
    def validate(cls, manifest: dict[str, Any]) -> dict[str, Any]:
        inputs = manifest.get("required_files", [])
        steps = manifest.get("steps", [])
        outputs = manifest.get("outputs", [])
        errors: list[str] = []
        warnings: list[str] = []

        for raw_step in steps:
            try:
                step = OperationStep.model_validate(raw_step)
                definition = get_operation(step.operation)
            except (TypeError, ValueError) as error:
                errors.append(str(error))
                continue

            step_type = step.operation
            missing = [
                parameter
                for parameter in definition.required_parameters
                if not step.parameters.get(parameter)
            ]
            if missing:
                errors.append(
                    f"{step_type} requer: {', '.join(missing)}."
                )
            if step_type == "filter" and not (
                step.parameters.get("condition")
                or step.parameters.get("column")
            ):
                errors.append("filter requer condition ou column.")
            if step_type in {"join", "reconcile"} and len(inputs) < 2:
                errors.append(
                    f"{step_type} identificado mas apenas 1 documento foi encontrado. "
                    "Join requer pelo menos duas entradas."
                )

        if steps and not outputs:
            errors.append("Pipeline válido requer pelo menos um output.")

        return {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
            "input_count": len(inputs),
            "step_count": len(steps),
            "output_count": len(outputs),
        }

    @classmethod
    def assert_valid(cls, manifest: dict[str, Any]) -> None:
        result = cls.validate(manifest)
        if not result["valid"]:
            raise ValueError("Pipeline inconsistente: " + " ".join(result["errors"]))