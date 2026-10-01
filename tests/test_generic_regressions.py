from core.ai_service import MockAIService
from core.document_resolver import DocumentResolver


def test_generic_sales_and_inventory_pipeline_is_not_domain_specific():
    analysis = MockAIService().analyze(
        "Recebo um CSV de vendas e outro CSV de estoque. "
        "Quero cruzar as bases e gerar um resumo."
    )

    assert [item["id"] for item in analysis.inputs] == ["vendas", "estoque"]
    assert [step["type"] for step in analysis.steps] == ["join"]
    assert analysis.pipeline_validation["valid"] is True
    assert analysis.execution_plan is not None
    assert analysis.execution_plan.suggestions[0]["operation"] == "aggregate"
    assert analysis.execution_plan.suggestions[0]["requires_confirmation"] is True


def test_explicit_grouping_is_a_pipeline_step_not_a_suggestion():
    analysis = MockAIService().analyze(
        "Recebo uma planilha de vendas. Quero agrupar por cliente."
    )

    aggregate = next(step for step in analysis.steps if step.operation == "aggregate")
    assert aggregate.parameters["group_by"] == "cliente"
    assert analysis.execution_plan is not None
    assert analysis.execution_plan.suggestions == []


def test_profile_grouping_candidate_stays_optional_until_confirmation():
    analysis = MockAIService().analyze(
        "Recebo dois relatórios ZSD008, um antigo e um novo. "
        "Quero comparar."
    )

    assert not any(step.operation == "aggregate" for step in analysis.steps)
    assert analysis.execution_plan is not None
    suggestion = analysis.execution_plan.suggestions[0]
    assert suggestion["parameters"]["group_by"] == "Razão Social"
    assert suggestion["source"] == ["perfil"]
    assert suggestion["requires_confirmation"] is True


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


def test_catalog_profiles_do_not_replace_generic_documents_in_a_mixed_prompt():
    prompt = "Recebo um Excel de vendas e outro de cadastro de clientes."

    entities = DocumentResolver().detect_file_entities(prompt)
    analysis = MockAIService().analyze(prompt)

    assert [entity["id"] for entity in entities] == ["vendas", "cadastro_clientes"]
    assert [item["id"] for item in analysis.inputs] == [
        "vendas",
        "cadastro_clientes",
    ]


def test_short_business_requirements_extract_all_requested_operations():
    analysis = MockAIService().analyze(
        "faturamento por regiao\n"
        "top 10 clientes\n"
        "vendas sem cliente cadastrado"
    )

    assert [step.operation for step in analysis.steps] == [
        "join",
        "aggregate",
        "top_n",
        "unmatched_records",
    ]
    aggregate = next(step for step in analysis.steps if step.operation == "aggregate")
    assert aggregate.parameters["group_by"] == "regiao"
    top_n = next(step for step in analysis.steps if step.operation == "top_n")
    assert top_n.parameters == {"group_by": "cliente", "limit": 10}
    unmatched = next(
        step for step in analysis.steps if step.operation == "unmatched_records"
    )
    assert unmatched.parameters == {
        "left_source": "vendas",
        "right_source": "cadastro_clientes",
    }
    assert unmatched.pending_confirmation == ["chave_join"]


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


def test_execution_plan_does_not_invent_keys_or_groupings():
    analysis = MockAIService().analyze(
        "Preciso comparar dois arquivos CSV e gerar um resultado."
    )

    assert analysis.execution_plan is not None
    transformations = analysis.execution_plan.transformations
    assert any(
        item["operation"] == "reconcile"
        and item["parameters"].get("key") is None
        and "chave_conciliacao" in item["pending_confirmation"]
        for item in transformations
    )
    serialized = str(analysis.execution_plan.model_dump())
    assert "'documento'" not in serialized
    assert "'grupo'" not in serialized
    assert "'itens'" not in serialized
    assert "'saldo'" not in serialized


def test_explicit_fs10n_reconciliation_uses_only_requested_key_and_quality_steps():
    analysis = MockAIService().analyze(
        "Recebo FS10N e Billing. Quero conciliar usando Conta e Nº documento."
    )

    assert analysis.pattern == "reconciliation"
    assert [step.operation for step in analysis.steps] == [
        "normalize",
        "reconcile",
        "validate",
    ]
    assert analysis.steps[1].parameters["key"] == ["Conta", "Nº documento"]
    reconcile = next(
        decision
        for decision in analysis.execution_plan.decisions
        if decision["operation"] == "reconcile"
    )
    assert reconcile["source"] == ["prompt"]


def test_explicit_key_overrides_profile_key():
    analysis = MockAIService().analyze(
        "Recebo ZSD008 e Billing. Quero conciliar usando CNPJ."
    )

    reconcile_step = next(step for step in analysis.steps if step.operation == "reconcile")
    reconcile_decision = next(
        decision
        for decision in analysis.execution_plan.decisions
        if decision["operation"] == "reconcile"
    )
    assert reconcile_step.parameters["key"] == "cnpj"
    assert reconcile_decision["source"] == ["prompt"]


def test_period_comparison_does_not_add_unrequested_aggregations():
    analysis = MockAIService().analyze(
        "Recebo dois relatórios ZSD008, um antigo e um novo. Quero comparar."
    )

    assert [step.operation for step in analysis.steps] == [
        "normalize",
        "reconcile",
        "validate",
    ]
    assert not any(step.operation == "aggregate" for step in analysis.steps)
    reconcile = next(
        decision
        for decision in analysis.execution_plan.decisions
        if decision["operation"] == "reconcile"
    )
    assert reconcile["source"] == ["perfil"]


def test_period_outputs_require_period_comparison_intent():
    without_period = MockAIService().analyze(
        "Preciso reconciliar duas bases financeiras."
    )
    with_period = MockAIService().analyze(
        "Preciso comparar os períodos antigo e novo."
    )

    assert "nfs_perdidas.xlsx" not in without_period.outputs
    assert "nfs_novas.xlsx" not in without_period.outputs
    assert "nfs_perdidas.xlsx" in with_period.outputs
    assert "nfs_novas.xlsx" in with_period.outputs


def test_execution_plan_exposes_confidence_sources_risks_and_output_reasons():
    analysis = MockAIService().analyze(
        "Preciso reconciliar duas bases financeiras."
    )
    assert analysis.execution_plan is not None
    plan = analysis.execution_plan

    assert plan.intent == "Conciliação de dados"
    assert plan.pattern == "reconciliation"
    assert "pedido menciona" in plan.pattern_reason
    assert plan.intent_confidence == "alta"
    assert plan.intent_source == ["prompt"]
    assert plan.intent_summary.startswith("O MELLO entendeu")
    assert plan.risks
    assert plan.output_details
    reconcile = next(item for item in plan.decisions if item["operation"] == "reconcile")
    assert reconcile["confidence"] == "baixa"
    assert reconcile["pending_confirmation"] == ["chave_conciliacao"]
    assert reconcile["source"] == []

    normalize = next(item for item in plan.decisions if item["operation"] == "normalize")
    validate = next(item for item in plan.decisions if item["operation"] == "validate")
    for automatic_step in (normalize, validate):
        assert automatic_step["confidence"] == "alta"
        assert automatic_step["source"] == ["regra_da_plataforma"]


def test_multi_step_sales_report_prompt_builds_rich_execution_plan():
    prompt = (
        "Recebo mensalmente uma planilha de vendas.\n\n"
        "Preciso:\n\n"
        "- considerar apenas o mes de julho;\n"
        "- remover registros onde Cliente esteja vazio;\n"
        "- remover registros onde Valor esteja vazio;\n"
        "- calcular o faturamento total por cliente;\n"
        "- calcular o faturamento total por produto;\n"
        "- identificar os 10 clientes com maior faturamento;\n"
        "- identificar os 10 produtos com maior faturamento;\n"
        "- gerar um resumo executivo;\n"
        "- gerar um diagnostico de possiveis problemas nos dados.\n\n"
        "Entregue o resultado em um unico workbook Excel."
    )

    analysis = MockAIService().analyze(prompt)
    assert analysis.execution_plan is not None

    operations = [step.operation for step in analysis.steps]
    assert operations == [
        "remove_nulls",
        "remove_nulls",
        "filter",
        "aggregate",
        "aggregate",
        "top_n",
        "top_n",
    ]

    null_columns = {
        step.parameters["column"]
        for step in analysis.steps
        if step.operation == "remove_nulls"
    }
    assert null_columns == {"cliente", "valor"}

    july_filter = next(step for step in analysis.steps if step.operation == "filter")
    assert july_filter.parameters["column"] is None
    assert july_filter.parameters["temporal_filter"] == "julho"
    assert july_filter.pending_confirmation == ["coluna_data"]
    assert july_filter.confidence == "baixa"

    aggregates = [step for step in analysis.steps if step.operation == "aggregate"]
    assert {step.parameters["group_by"] for step in aggregates} == {"cliente", "produto"}
    assert all(step.parameters["sum"] == ["valor"] for step in aggregates)
    assert all(step.confidence == "alta" for step in aggregates)

    top_n_steps = [step for step in analysis.steps if step.operation == "top_n"]
    assert {step.parameters["group_by"] for step in top_n_steps} == {"cliente", "produto"}
    assert all(step.parameters["limit"] == 10 for step in top_n_steps)
    assert all(step.parameters["order_by"] == "valor" for step in top_n_steps)

    assert analysis.outputs == [
        "totais_por_cliente.xlsx",
        "totais_por_produto.xlsx",
        "top_10_por_cliente.xlsx",
        "top_10_por_produto.xlsx",
        "resumo_executivo.xlsx",
        "diagnostico.xlsx",
    ]
    assert analysis.pipeline_validation["valid"] is True

    assert analysis.manifest_data["output_mode"] == "workbook"
    assert analysis.manifest_data["outputs"] == ["resultado.xlsx"]
    assert analysis.manifest_data["workbook_sheets"] == analysis.outputs

    assert analysis.execution_plan.intent_summary == (
        "O MELLO entendeu que você deseja analisar vendas de julho, "
        "eliminar registros inválidos, calcular faturamento por cliente e produto, "
        "gerar rankings dos maiores resultados e produzir um resumo executivo "
        "com diagnóstico. Tudo será entregue em um único arquivo Excel."
    )


def test_prompted_workbook_sheet_names_are_preserved_in_manifest():
    analysis = MockAIService().analyze(
        "Recebo FS10N e Billing em um único workbook com as abas: "
        "Resumo Executivo, Conciliados, Divergências, Apenas FS10N e Apenas Billing."
    )

    assert analysis.outputs == [
        "Resumo Executivo",
        "Conciliados",
        "Divergências",
        "Apenas FS10N",
        "Apenas Billing",
    ]
    assert analysis.manifest_data["output_mode"] == "workbook"
    assert analysis.manifest_data["outputs"] == ["resultado.xlsx"]
    assert analysis.manifest_data["workbook_sheets"] == analysis.outputs