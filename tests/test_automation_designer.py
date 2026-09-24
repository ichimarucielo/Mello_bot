import subprocess
import sys
from pathlib import Path

import yaml
import pandas as pd
from fastapi import HTTPException

from api.app import (
    analyze_automation,
    create_automation_project,
    generate_automation_manifest,
)
from api.schemas import (
    AICreateProjectRequest,
    AIAnalyzeResponse,
    AICreateProjectResponse,
)
from core.ai_service import AIService, MockAIService
from core.automation_designer import AutomationDesigner
from core.models import AutomationAnalysis, AutomationRequest, Manifest
from core.registry import load_projects


PROMPT = "Recebo diariamente um relatório FS10N exportado do SAP e um relatório de Billing."


def test_mock_ai_service_returns_structured_analysis():
    analysis = MockAIService().analyze(PROMPT)

    assert isinstance(analysis, AutomationAnalysis)
    assert analysis.project_id == "conciliacao_fs10n_billing"
    assert analysis.category == "financeiro"
    assert {item["id"] for item in analysis.inputs} == {"fs10n", "billing"}
    assert analysis.outputs == ["conciliacao.xlsx", "divergencias.xlsx"]


def test_sap_report_aliases_use_financial_xlsx_defaults():
    service = MockAIService()

    expected_ids = {
        "FS10N": "fs10n",
        "FBL3N": "fbl3n",
        "FBL5N": "fbl5n_aberta",
        "ZSD008": "zsd008",
    }
    for report_name in expected_ids:
        analysis = service.analyze(f"Recebo o relatorio {report_name} do SAP.")

        assert analysis.category == "financeiro"
        assert analysis.inputs[0]["id"] == expected_ids[report_name]
        assert analysis.inputs[0]["extension"] == "xlsx"
        assert analysis.manifest_data["required_files"][0]["accepted_extensions"] == [
            "xlsx"
        ]


def test_billing_and_prefeitura_remain_distinct_sources():
    service = MockAIService()

    billing = service.analyze("Recebo um relatorio de Billing.")
    prefeitura = service.analyze("Recebo um arquivo exportado da Prefeitura.")

    assert billing.inputs[0]["id"] == "billing"
    assert billing.inputs[0]["extension"] == "xlsx"
    assert prefeitura.inputs[0]["id"] == "prefeitura_nfse"
    assert prefeitura.inputs[0]["extension"] == "csv"


def test_file_entities_separate_zsd008_by_month():
    analysis = MockAIService().analyze(
        "Recebo um ZSD008 do mes 7 e outro ZSD008 do mes 8."
    )

    assert [item["id"] for item in analysis.inputs] == [
        "zsd008_mes_7",
        "zsd008_mes_8",
    ]
    assert all(item["source"] == "sap" for item in analysis.inputs)
    assert all(item["extension"] == "xlsx" for item in analysis.inputs)


def test_file_entities_separate_fbl5n_by_status():
    analysis = MockAIService().analyze(
        "Recebo FBL5N aberta e FBL5N compensada."
    )

    assert [item["id"] for item in analysis.inputs] == [
        "fbl5n_aberta",
        "fbl5n_compensada",
    ]


def test_file_entities_separate_fs10n_by_period():
    analysis = MockAIService().analyze(
        "Recebo FS10N atual e FS10N anterior."
    )

    assert [item["id"] for item in analysis.inputs] == [
        "fs10n_atual",
        "fs10n_anterior",
    ]


def test_mock_ai_service_recognizes_accounts_payable_and_receivable():
    analysis = MockAIService().analyze(
        "Recebo uma base de contas a pagar e outra de contas a receber "
        "e preciso identificar divergencias."
    )

    assert analysis.project_id == "conciliacao_contas_pagar_receber"
    assert analysis.category == "financeiro"
    assert [item["id"] for item in analysis.inputs] == [
        "contas_pagar",
        "contas_receber",
    ]
    assert analysis.outputs == ["conciliacao.xlsx", "divergencias.xlsx"]


def test_mock_ai_service_recognizes_consolidation():
    analysis = MockAIService().analyze(
        "Preciso consolidar os arquivos mensais de vendas em um unico arquivo."
    )

    assert analysis.project_id == "consolidacao_dados"
    assert analysis.outputs == ["consolidado.xlsx"]


def test_mock_ai_service_recognizes_power_bi_dataset():
    analysis = MockAIService().analyze(
        "Preciso preparar um dataset para um dashboard no Power BI."
    )

    assert analysis.project_id == "dataset_power_bi"
    assert analysis.category == "power_bi"
    assert analysis.outputs == ["dataset.csv"]


def test_mock_ai_service_keeps_generic_fallback_without_context():
    analysis = MockAIService().analyze("Preciso automatizar um processo.")

    assert analysis.project_id == "automacao"
    assert analysis.inputs[0]["id"] == "entrada"
    assert analysis.outputs == ["resultado.xlsx"]


def test_designer_accepts_injected_ai_service():
    class FixedAIService(AIService):
        def analyze(self, prompt: str) -> AutomationAnalysis:
            return MockAIService().analyze(prompt)

    analysis = AutomationDesigner(FixedAIService()).analyze(PROMPT)

    assert analysis.category == "financeiro"


def test_designer_generates_valid_manifest(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("core.project_scaffolder.BASE_DIR", tmp_path)
    designer = AutomationDesigner()

    manifest = yaml.safe_load(designer.generate_manifest(PROMPT))

    validated = Manifest.model_validate(manifest)
    assert validated.id == "conciliacao_fs10n_billing"
    assert len(validated.required_files) == 2
    assert [item.id for item in validated.required_files] == ["fs10n", "billing"]
    assert validated.outputs == ["conciliacao.xlsx", "divergencias.xlsx"]


def test_designer_creates_project_artifacts_and_executable_main(
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.setattr("core.project_scaffolder.BASE_DIR", tmp_path)

    result = AutomationDesigner().create_project(PROMPT)
    project_path = Path(result.project_path)
    input_one = tmp_path / "fs10n.xlsx"
    input_two = tmp_path / "billing.xlsx"
    frame = pd.DataFrame({"DOCUMENTO": ["1"], "VALOR": [10]})
    frame.to_excel(input_one, index=False)
    frame.to_excel(input_two, index=False)

    process = subprocess.run(
        [
            sys.executable,
            result.entrypoint_path,
            "--fs10n",
            str(input_one),
            "--billing",
            str(input_two),
        ],
        cwd=project_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.status == "created"
    assert Path(result.manifest_path).is_file()
    assert Path(result.readme_path).is_file()
    assert Path(result.entrypoint_path).is_file()
    assert process.returncode == 0, process.stderr
    assert (project_path / "data" / "output" / "conciliacao.xlsx").is_file()
    assert (project_path / "data" / "output" / "divergencias.xlsx").is_file()


def test_designer_publishes_manifest_and_registry_discovers_project(
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.setattr("core.project_scaffolder.BASE_DIR", tmp_path)
    monkeypatch.setattr("core.automation_designer.MANIFESTS_DIR", tmp_path / "manifests")
    monkeypatch.setattr("core.manifest_loader.MANIFESTS_PATH", tmp_path / "manifests")
    monkeypatch.setattr("core.registry.MANIFESTS_DIR", tmp_path / "manifests")

    result = AutomationDesigner().create_project(PROMPT)
    project_manifest = Path(result.manifest_path)
    published_manifest = tmp_path / "manifests" / "conciliacao_fs10n_billing.yaml"

    assert project_manifest == (
        tmp_path / "projects" / "conciliacao_fs10n_billing" / "manifest.yaml"
    )
    assert project_manifest.is_file()
    assert published_manifest.is_file()
    assert project_manifest.read_text(encoding="utf-8") == published_manifest.read_text(
        encoding="utf-8"
    )
    assert "conciliacao_fs10n_billing" in load_projects()
    assert result.published_manifest_path == str(published_manifest)


def test_designer_selects_pattern_templates(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("core.project_scaffolder.BASE_DIR", tmp_path)
    designer = AutomationDesigner()

    prompts_and_markers = {
        "Comparar contas a pagar e contas a receber": "def reconcile(",
        "Consolidar os arquivos mensais de vendas": "pd.concat",
        "Classificar uma base de antifraude e identificar risco": "validate_input",
        "Preparar um dataset para Power BI": "to_csv",
        "Validar registros de clientes": "def validate_input",
        "Executar uma automacao simples": "TODO: implementar",
    }
    for index, (prompt, marker) in enumerate(prompts_and_markers.items()):
        result = designer.create_project(f"{prompt} {index}")
        generated = Path(result.entrypoint_path).read_text(encoding="utf-8")
        assert marker in generated


def test_ai_endpoints_return_expected_contract(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("core.project_scaffolder.BASE_DIR", tmp_path)
    request = AutomationRequest(prompt=PROMPT)

    analysis_response = AIAnalyzeResponse.model_validate(
        analyze_automation(request).model_dump()
    )
    manifest_response = generate_automation_manifest(request)
    create_response = AICreateProjectResponse.model_validate(
        create_automation_project(
            AICreateProjectRequest(
                prompt=PROMPT,
                approved=True,
            )
        )
    )

    assert analysis_response.complexity == "media"
    assert analysis_response.execution_plan["documents"]
    assert analysis_response.execution_plan["transformations"]
    assert Manifest.model_validate(yaml.safe_load(manifest_response["manifest"]))
    assert create_response.status == "created"


def test_ai_create_project_requires_human_approval():
    try:
        create_automation_project(
            AICreateProjectRequest(prompt=PROMPT)
        )
    except HTTPException as error:
        assert error.status_code == 409
        assert "aprovação humana" in error.detail
    else:
        raise AssertionError("A criação deveria exigir aprovação humana.")