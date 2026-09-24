from core.ai_service import MockAIService
from core.manifest_generator import ManifestGenerator
from core.pipeline_catalog import SUPPORTED_OPERATIONS, get_operation
from core.pipeline_validator import PipelineValidator


def test_operation_catalog_is_domain_agnostic_and_categorized():
    operations = {item.operation: item for item in SUPPORTED_OPERATIONS}

    assert {
        "filter",
        "calculate",
        "join",
        "reconcile",
        "aggregate",
        "sort",
        "rename_columns",
        "drop_columns",
        "normalize",
        "deduplicate",
        "drop_nulls",
        "fill_nulls",
        "export",
    } <= operations.keys()
    assert operations["filter"].category == "transformation"
    assert operations["export"].category == "output"
    assert get_operation("calculate").required_parameters == ("column", "formula")


def test_mock_ai_extracts_generic_operation_parameters():
    analysis = MockAIService().analyze(
        "Recebo dois arquivos CSV. Considere apenas julho. "
        "Remova registros nulos. "
        "Crie coluna saldo = valor_aberto - valor_recebido. "
        "Agrupe por cliente. "
        "Remova as colunas observacao e comentarios. "
        "Renomear cliente para cliente_nome."
    )

    steps = analysis.manifest_data["steps"]
    assert {step["type"] for step in steps} >= {
        "remove_nulls",
        "filter",
        "calculate",
        "aggregate",
        "drop_columns",
        "rename_columns",
    }

    calculate = next(step for step in steps if step["type"] == "calculate")
    assert calculate["column"] == "saldo"
    assert calculate["formula"] == "valor_aberto - valor_recebido"

    manifest = ManifestGenerator.validate(analysis.manifest_data)
    canonical_steps = [step.model_dump() for step in manifest.steps]
    assert any(
        step["operation"] == "drop_nulls"
        for step in canonical_steps
    )
    assert any(
        step["operation"] == "calculate"
        and step["parameters"]["column"] == "saldo"
        for step in canonical_steps
    )


def test_pipeline_validator_checks_operation_parameters():
    base = {
        "required_files": [{"id": "one"}, {"id": "two"}],
        "outputs": ["result.xlsx"],
    }
    invalid_steps = [
        {"operation": "calculate", "parameters": {"column": "saldo"}},
        {"operation": "aggregate", "parameters": {}},
        {"operation": "rename_columns", "parameters": {}},
        {"operation": "drop_columns", "parameters": {}},
        {"operation": "reconcile", "parameters": {}},
    ]

    result = PipelineValidator.validate({**base, "steps": invalid_steps})

    assert not result["valid"]
    assert any("calculate requer" in error for error in result["errors"])
    assert any("aggregate requer" in error for error in result["errors"])
    assert any("rename_columns requer" in error for error in result["errors"])
    assert any("drop_columns requer" in error for error in result["errors"])
    assert any("reconcile requer" in error for error in result["errors"])
