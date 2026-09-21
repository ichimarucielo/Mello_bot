import subprocess
import sys
from pathlib import Path

import yaml

from api.app import (
    analyze_automation,
    create_automation_project,
    generate_automation_manifest,
)
from api.schemas import AIAnalyzeResponse, AICreateProjectResponse
from core.ai_service import AIService, MockAIService
from core.automation_designer import AutomationDesigner
from core.models import AutomationAnalysis, AutomationRequest, Manifest


PROMPT = "Recebo diariamente um relatório FS10N exportado do SAP e um relatório de Billing."


def test_mock_ai_service_returns_structured_analysis():
    analysis = MockAIService().analyze(PROMPT)

    assert isinstance(analysis, AutomationAnalysis)
    assert analysis.project_id == "conciliacao_sap_billing"
    assert analysis.category == "financeiro"
    assert {item["id"] for item in analysis.inputs} == {"sap", "billing"}
    assert analysis.outputs == ["conciliacao.xlsx", "divergencias.xlsx"]


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
    assert validated.id == "conciliacao_sap_billing"
    assert len(validated.required_files) == 2
    assert [item.id for item in validated.required_files] == ["sap", "billing"]
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
    input_one.write_bytes(b"placeholder")
    input_two.write_bytes(b"placeholder")

    process = subprocess.run(
        [
            sys.executable,
            result.entrypoint_path,
            "--sap",
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


def test_ai_endpoints_return_expected_contract(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("core.project_scaffolder.BASE_DIR", tmp_path)
    request = AutomationRequest(prompt=PROMPT)

    analysis_response = AIAnalyzeResponse.model_validate(
        analyze_automation(request).model_dump()
    )
    manifest_response = generate_automation_manifest(request)
    create_response = AICreateProjectResponse.model_validate(
        create_automation_project(request)
    )

    assert analysis_response.complexity == "media"
    assert Manifest.model_validate(yaml.safe_load(manifest_response["manifest"]))
    assert create_response.status == "created"