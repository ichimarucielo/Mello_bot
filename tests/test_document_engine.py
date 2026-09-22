from core.ai_service import MockAIService
from core.document_catalog import DocumentCatalog
from core.document_engine import DocumentDefinition, DocumentMatcher


def test_catalog_matches_documents_without_exposing_source_as_identity():
    catalog = DocumentCatalog()

    matches = catalog.match("Recebi Em Aberto e Recebimento")

    assert [document.id for document in matches] == [
        "fbl5n_aberta",
        "fbl5n_compensada",
    ]
    assert all(document.source == "sap" for document in matches)


def test_document_matcher_uses_document_aliases():
    matcher = DocumentMatcher(
        [
            DocumentDefinition(
                id="entrada_clientes",
                name="Entrada de Clientes",
                aliases=("clientes", "cadastro de clientes"),
            )
        ]
    )

    assert [document.id for document in matcher.match("arquivo de clientes")] == [
        "entrada_clientes"
    ]


def test_analysis_manifest_uses_document_ids_for_required_files():
    analysis = MockAIService().analyze(
        "Recebi dois documentos: Em Aberto e Recebimento. "
        "Representam titulos em aberto e compensados do SAP. "
        "Preciso cruzar ambas as bases."
    )

    assert [item["id"] for item in analysis.manifest_data["required_files"]] == [
        "fbl5n_aberta",
        "fbl5n_compensada",
    ]
    assert all(item["id"] != "sap" for item in analysis.inputs)


def test_fbl5n_reconciliation_project_uses_document_family():
    analysis = MockAIService().analyze(
        "Recebi Em aberto e Recebimento. Preciso cruzar ambas as bases."
    )

    assert analysis.project_id == "conciliacao_fbl5n"
    assert analysis.project_name == "Conciliacao FBL5N"
    assert [item["id"] for item in analysis.manifest_data["required_files"]] == [
        "fbl5n_aberta",
        "fbl5n_compensada",
    ]


def test_pipeline_assistant_creates_manifest_steps_and_derived_outputs():
    analysis = MockAIService().analyze(
        "Recebi FBL5N Aberta e Recebimento. Quero remover nulos, "
        "considerar somente julho de 2026, criar saldo, "
        "saldo = aberto - pago e gerar resumo por empresa."
    )

    assert [step["type"] for step in analysis.steps] == [
        "normalize",
        "remove_nulls",
        "filter",
        "calculate",
        "aggregate",
        "reconcile",
    ]
    assert analysis.steps[2]["value"] == "2026-07"
    assert analysis.steps[3] == {
        "type": "calculate",
        "column": "saldo",
        "formula": "aberto - pago",
    }
    assert analysis.outputs == [
        "conciliacao_julho.xlsx",
        "resumo_empresas.xlsx",
    ]
    assert analysis.manifest_data["steps"] == analysis.steps


def test_pipeline_operations_are_document_agnostic():
    analysis = MockAIService().analyze(
        "Recebo dois arquivos CSV. Quero cruzar pelo CNPJ, remover duplicados "
        "e validar os dados antes de exportar o resultado."
    )

    assert [step["type"] for step in analysis.steps] == [
        "deduplicate",
        "join",
        "validate",
        "export",
    ]
    assert analysis.steps[1] == {
        "type": "join",
        "left_key": "cnpj",
        "right_key": "cnpj",
    }
    assert all(item["id"] not in {"sap", "billing", "prefeitura"} for item in analysis.inputs)


def test_pipeline_assistant_derives_generic_output_from_intent():
    analysis = MockAIService().analyze(
        "Recebo dois CSVs. Quero cruzar pelo CNPJ. Remover duplicados. "
        "Remover registros sem CNPJ. Calcular percentual: "
        "valor_cliente / valor_total. Agrupar por cliente. "
        "Exportar um resumo final."
    )

    assert [step["type"] for step in analysis.steps] == [
        "deduplicate",
        "remove_nulls",
        "join",
        "calculate",
        "aggregate",
        "export",
    ]
    assert analysis.steps[1] == {
        "type": "remove_nulls",
        "column": "cnpj",
    }
    assert analysis.steps[2] == {
        "type": "join",
        "left_key": "cnpj",
        "right_key": "cnpj",
    }
    assert analysis.steps[3] == {
        "type": "calculate",
        "column": "percentual",
        "formula": "valor_cliente / valor_total",
    }
    assert analysis.outputs == ["resumo_clientes.xlsx"]
    assert analysis.inputs[0]["extension"] == "csv"


def test_planilha_input_prefers_excel_extension():
    analysis = MockAIService().analyze("Recebo uma planilha de vendas.")

    assert analysis.inputs[0]["extension"] == "xlsx"
    assert analysis.inputs[0]["display_name"] == "Arquivo de entrada"


def test_understanding_summarizes_generic_sales_pipeline():
    analysis = MockAIService().analyze(
        "Recebi um relatório de vendas e um relatório de clientes. "
        "Quero cruzar pelo CNPJ, criar margem, agrupar por cliente "
        "e gerar um resumo final."
    )

    assert [item["id"] for item in analysis.inputs] == [
        "vendas",
        "cadastro_clientes",
    ]
    assert analysis.project_id == "resumo_clientes_vendas"
    assert analysis.project_name == "Análise de Margem por Cliente"
    assert analysis.understanding == {
        "document_count": 2,
        "documents": [
            {"id": "vendas", "display_name": "Relatório de Vendas"},
            {"id": "cadastro_clientes", "display_name": "Cadastro de Clientes"},
        ],
        "operations": ["join", "calculate", "aggregate"],
        "operation_count": 3,
        "outputs": ["resumo_clientes.xlsx"],
        "output_count": 1,
        "project_name": "Análise de Margem por Cliente",
    }