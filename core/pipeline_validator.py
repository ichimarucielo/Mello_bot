from typing import Any


class PipelineValidator:
    """Valida a coerência estrutural de um pipeline declarativo."""

    @classmethod
    def validate(cls, manifest: dict[str, Any]) -> dict[str, Any]:
        inputs = manifest.get("required_files", [])
        steps = manifest.get("steps", [])
        outputs = manifest.get("outputs", [])
        errors: list[str] = []
        warnings: list[str] = []

        for step in steps:
            step_type = step.get("type")
            if step_type == "join" and len(inputs) < 2:
                errors.append(
                    "Join identificado mas apenas 1 documento foi encontrado. "
                    "Join requer pelo menos duas entradas."
                )
            elif step_type == "reconcile" and len(inputs) < 2:
                errors.append(
                    "Reconciliação identificada mas apenas 1 documento foi encontrado. "
                    "Reconciliação requer pelo menos duas entradas."
                )
            elif step_type == "calculate":
                if not step.get("column") or not step.get("formula"):
                    errors.append("Fórmula pendente de definição.")
            elif step_type == "aggregate" and not step.get("group_by"):
                errors.append("Aggregate requer group_by.")
            elif step_type == "filter" and not step.get("column"):
                errors.append("Filter requer column.")

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