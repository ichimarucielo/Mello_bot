from dataclasses import dataclass


@dataclass(frozen=True)
class PipelineOperation:
    name: str
    aliases: tuple[str, ...]


OPERATIONS = (
    PipelineOperation("normalize", ("normalizar", "normalizacao", "padronizar")),
    PipelineOperation(
        "remove_nulls",
        ("remover nulos", "remover registros sem", "sem nulos", "tirar nulos"),
    ),
    PipelineOperation("deduplicate", ("remover duplicados", "sem duplicados")),
    PipelineOperation("filter", ("somente", "apenas", "filtrar")),
    PipelineOperation("join", ("cruzar", "juntar", "unir", "relacionar")),
    PipelineOperation("calculate", ("calcular", "criar coluna", "formula")),
    PipelineOperation("aggregate", ("agrupar", "somar por", "totalizar", "resumo")),
    PipelineOperation("validate", ("validar", "validacao", "conferir")),
    PipelineOperation("export", ("exportar", "gerar arquivo", "salvar resultado")),
    PipelineOperation("reconcile", ("conciliar", "confrontar", "identificar diferencas")),
)


def mentions(prompt: str, operation: str) -> bool:
    definition = next(item for item in OPERATIONS if item.name == operation)
    return any(alias in prompt for alias in definition.aliases)