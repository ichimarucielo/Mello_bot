from core.pipeline_catalog import get_operation
from core.models import OperationStep
from typing import Any, Dict, List
import logging

logger = logging.getLogger(__name__)

# Chaves que frequentemente causam erro de tipo no Pandas se não normalizadas
SENSITIVE_MERGE_KEYS = {"cnpj", "cpf", "cnpj_cpf", "nu_cnpj", "nu_cpf"}

# Tipos de chaves e suas regras de normalização
KEY_TYPE_RULES = {
    "cnpj": {"length": 14, "message": "Formato esperado: 14 dígitos (ex: 00.000.000/0001-00)"},
    "cpf": {"length": 11, "message": "Formato esperado: 11 dígitos (ex: 000.000.000-00)"},
}

def validate_pipeline(steps: List[OperationStep]) -> List[str]:
    """Valida operações de pipeline e retorna warnings."""
    warnings = []
    
    if not steps:
        warnings.append("Pipeline vazio: Nenhuma operação definida.")
        return warnings

    for i, step in enumerate(steps):
        op = step.operation
        
        if op in {"join", "reconcile"}:
            key = step.parameters.get("key")
            
            # 1. Valida presença da chave
            if not key:
                warnings.append(
                    f"Passo {i+1} ({op}): operação de merge sem 'key' definida. "
                    f"Isso pode causar erros de tipo (int64 vs str) no Pandas."
                )
            else:
                # 2. Valida normalização de chaves sensíveis
                key_lower = str(key).lower()
                if any(sensitive in key_lower for sensitive in SENSITIVE_MERGE_KEYS):
                    # Verifica se a normalização está habilitada
                    normalize_key = step.parameters.get("normalize_key", False)
                    if not normalize_key:
                        warnings.append(
                            f"Passo {i+1} ({op}): A chave '{key}' é um identificador fiscal. "
                            f"Habilite 'normalize_key: true' nos parâmetros ou adicione uma etapa "
                            f"'normalize_key' antes deste passo."
                        )
                    
                    # Verifica tipo da chave
                    key_type = None
                    for kt in KEY_TYPE_RULES:
                        if kt in key_lower:
                            key_type = kt
                            break
                    
                    if key_type:
                        rules = KEY_TYPE_RULES[key_type]
                        warnings.append(
                            f"Passo {i+1} ({op}): A chave '{key}' é do tipo {key_type.upper()}. "
                            f"{rules['message']}"
                        )
                    
        elif op == "aggregate":
            if not step.parameters.get("group_by"):
                warnings.append(f"Passo {i+1} (aggregate): requer 'group_by' em parameters.")
                
        elif op == "calculate":
            if not step.parameters.get("formula") or not step.parameters.get("column"):
                warnings.append(f"Passo {i+1} (calculate): requer 'column' e 'formula' em parameters.")

    return warnings


class PipelineValidator:
    """Valida a coerência estrutural de um pipeline declarativo."""

    @classmethod
    def validate(cls, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """Valida manifesto e retorna status com erros e warnings."""
        inputs = manifest.get("required_files", [])
        pipeline = manifest.get("pipeline") or {}
        steps = manifest.get("steps", []) or pipeline.get("operations", [])
        outputs = manifest.get("outputs", [])
        errors: List[str] = []
        warnings: List[str] = []

        # Validações básicas
        if not steps:
            errors.append("Pipeline vazio: Nenhuma operação definida.")
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings,
                "input_count": len(inputs),
                "step_count": len(steps),
                "output_count": len(outputs),
            }

        # Valida cada passo
        for i, raw_step in enumerate(steps):
            try:
                step = OperationStep.model_validate(raw_step)
                definition = get_operation(step.operation)
            except (TypeError, ValueError) as error:
                errors.append(f"Passo {i+1}: {str(error)}")
                continue

            # Valida parâmetros obrigatórios
            missing = [
                param for param in definition.required_parameters
                if not step.parameters.get(param)
            ]
            if missing:
                pending = set(step.pending_confirmation)
                unresolved = {
                    "key": {"chave_join", "chave_conciliacao"},
                    "group_by": {"agrupamento"},
                }
                if any(
                    conf in pending
                    for param in missing
                    for conf in unresolved.get(param, set())
                ):
                    warnings.append(
                        f"Passo {i+1} ({step.operation}): aguarda confirmação para {', '.join(missing)}."
                    )
                else:
                    errors.append(
                        f"Passo {i+1} ({step.operation}): requer {', '.join(missing)}."
                    )

            # Validações específicas por tipo de operação
            if step.operation == "filter" and not (
                step.parameters.get("condition")
                or step.parameters.get("column")
            ):
                errors.append("Passo filter: requer condition ou column.")
                
            if step.operation in {"join", "reconcile"} and len(inputs) < 2:
                errors.append(
                    f"Passo {step.operation}: requer pelo menos duas entradas."
                )

            # Validação de normalização (novo)
            if step.operation in {"join", "reconcile"}:
                key = step.parameters.get("key")
                key_columns = key if isinstance(key, (list, tuple)) else [key]
                has_sensitive_key = any(
                    sensitive in str(column).lower()
                    for column in key_columns
                    for sensitive in SENSITIVE_MERGE_KEYS
                )
                if key and has_sensitive_key:
                    if not step.parameters.get("normalize_key", False):
                        warnings.append(
                            f"Passo {i+1} ({step.operation}): Chave sensível '{key}' "
                            "requer normalização. Adicione 'normalize_key: true' ou "
                            "uma etapa 'normalize_key' antes deste passo."
                        )

        # Valida de outputs
        if steps and not outputs:
            errors.append("Pipeline válido requer pelo menos um output.")

        # Registra resultado da validação
        validation_result = {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
            "input_count": len(inputs),
            "step_count": len(steps),
            "output_count": len(outputs),
        }
        
        logger.info(f"Validação de pipeline: {validation_result}")
        return validation_result

    @classmethod
    def assert_valid(cls, manifest: Dict[str, Any]) -> None:
        """Valida manifesto e levanta exceção se inválido."""
        result = cls.validate(manifest)
        if not result["valid"]:
            error_msg = "Pipeline inválido:\n" + "\n".join(
                f"- {error}" for error in result["errors"]
            )
            if result["warnings"]:
                error_msg += "\n\nWarnings:\n" + "\n".join(
                    f"- {warning}" for warning in result["warnings"]
                )
            raise ValueError(error_msg)
