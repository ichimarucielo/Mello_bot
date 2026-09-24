from core.document_resolver import DocumentResolver


def test_resolver_uses_catalog_profiles_without_domain_logic():
    plan = DocumentResolver().build_execution_plan(
        "Recebo FS10N e Billing e preciso conciliar pela chave documento.",
        outputs=["resultado.xlsx"],
    )

    assert {item["id"] for item in plan.profiles} == {"fs10n", "billing"}
    assert plan.outputs == ["resultado.xlsx"]
    assert plan.documents


def test_resolver_falls_back_to_generic_documents():
    plan = DocumentResolver().build_execution_plan(
        "Recebo uma planilha de vendas e outra de clientes.",
        outputs=["resumo.xlsx"],
    )

    assert plan.profiles == []
    assert [item["id"] for item in plan.documents] == ["vendas", "clientes"]


def test_resolver_reports_missing_relation_key_for_multiple_inputs():
    plan = DocumentResolver().build_execution_plan(
        "Recebo dois arquivos CSV e preciso juntar as bases.",
        outputs=["resultado.xlsx"],
    )

    assert plan.open_questions == ["Qual chave deve relacionar os documentos?"]