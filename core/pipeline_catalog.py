from dataclasses import dataclass


@dataclass(frozen=True)
class OperationDefinition:
    operation: str
    description: str
    aliases: tuple[str, ...]
    category: str = "transformation"
    required_parameters: tuple[str, ...] = ()


SUPPORTED_OPERATIONS = (
    OperationDefinition(
        "filter", "Filtra registros conforme uma condição.",
        ("filtrar", "somente", "apenas"), required_parameters=("condition",),
    ),
    OperationDefinition(
        "calculate", "Cria ou calcula uma coluna.",
        ("calcular", "criar coluna", "formula"),
        required_parameters=("column", "formula"),
    ),
    OperationDefinition(
        "join", "Combina documentos por uma chave.",
        ("cruzar", "juntar", "unir", "relacionar"),
        required_parameters=("key",),
    ),
    OperationDefinition(
        "reconcile", "Reconcilia documentos por uma chave.",
        ("conciliar", "confrontar", "identificar diferencas"),
        required_parameters=("key",),
    ),
    OperationDefinition(
        "aggregate", "Agrupa e resume registros.",
        ("agrupar", "agrupe por", "somar por", "totalizar", "resumo"),
        required_parameters=("group_by",),
    ),
    OperationDefinition(
        "top_n", "Seleciona os maiores registros de um agrupamento.",
        ("maiores", "top", "ranking", "principais"),
        required_parameters=("group_by", "limit"),
    ),
    OperationDefinition(
        "unmatched_records", "Identifica registros sem correspondência em outra base.",
        ("sem cliente cadastrado", "sem correspondencia", "nao encontrado"),
    ),
    OperationDefinition("sort", "Ordena registros.", ("ordenar", "ordenado", "sort")),
    OperationDefinition(
        "rename_columns", "Renomeia colunas.",
        ("renomear colunas", "renomeie", "renomear"),
        required_parameters=("mapping",),
    ),
    OperationDefinition(
        "drop_columns", "Remove colunas.",
        ("remover colunas", "remova as colunas", "excluir colunas"),
        required_parameters=("columns",),
    ),
    OperationDefinition(
        "normalize", "Padroniza dados e colunas.",
        ("normalizar", "normalizacao", "padronizar"),
    ),
    OperationDefinition(
        "deduplicate", "Remove registros duplicados.",
        ("remover duplicados", "sem duplicados"),
    ),
    OperationDefinition(
        "drop_nulls", "Remove registros com valores nulos.",
        (
            "remover nulos",
            "remova nulos",
            "remover registros sem",
            "remova registros nulos",
            "sem nulos",
            "tirar nulos",
        ),
    ),
    OperationDefinition(
        "remove_nulls", "Alias legado de drop_nulls.",
        (
            "remover nulos",
            "remova nulos",
            "remover registros sem",
            "remova registros nulos",
            "sem nulos",
            "tirar nulos",
        ),
    ),
    OperationDefinition("fill_nulls", "Preenche valores nulos.", ("preencher nulos", "substituir nulos")),
    OperationDefinition(
        "validate", "Valida registros e regras de qualidade.",
        ("validar", "validacao", "conferir"),
    ),
    OperationDefinition("export", "Gera um arquivo de saída.", ("exportar", "gerar arquivo", "salvar resultado"), category="output"),
)

OPERATIONS = SUPPORTED_OPERATIONS


def get_operation(operation: str) -> OperationDefinition:
    for definition in SUPPORTED_OPERATIONS:
        if definition.operation == operation:
            return definition
    raise ValueError(f"Operação não suportada: {operation}")


def mentions(prompt: str, operation: str) -> bool:
    definition = get_operation(operation)
    return any(alias in prompt for alias in definition.aliases)