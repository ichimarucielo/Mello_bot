from core.ai_service import MockAIService


def test_generic_sales_and_inventory_pipeline_is_not_domain_specific():
    analysis = MockAIService().analyze(
        "Recebo um CSV de vendas e outro CSV de estoque. "
        "Quero cruzar as bases e gerar um resumo."
    )

    assert [item["id"] for item in analysis.inputs] == ["vendas", "estoque"]
    assert [step["type"] for step in analysis.steps] == ["join", "aggregate"]
    assert analysis.pipeline_validation["valid"] is True


def test_generic_customer_period_inputs_are_supported():
    analysis = MockAIService().analyze(
        "Recebo um relatório de vendas e outro relatório de clientes. "
        "Quero cruzar as bases por CNPJ e gerar um resumo."
    )

    assert [item["id"] for item in analysis.inputs] == [
        "vendas",
        "cadastro_clientes",
    ]
    assert any(step["type"] == "join" for step in analysis.steps)
    assert analysis.pipeline_validation["valid"] is True


def test_two_unprofiled_spreadsheets_use_generic_fallback():
    analysis = MockAIService().analyze(
        "Recebo dois arquivos CSV de entrada. "
        "Quero validar e exportar o resultado."
    )

    assert [item["id"] for item in analysis.inputs] == [
        "entrada_1",
        "entrada_2",
    ]
    assert all(item["source"] == "generic" for item in analysis.inputs)
    assert analysis.pipeline_validation["valid"] is True


def test_unknown_document_description_keeps_generic_single_input_fallback():
    analysis = MockAIService().analyze(
        "Preciso automatizar o processamento de um documento desconhecido."
    )

    assert analysis.inputs[0]["id"] == "entrada"
    assert analysis.project_id == "automacao"
    assert analysis.outputs == ["resultado.xlsx"]