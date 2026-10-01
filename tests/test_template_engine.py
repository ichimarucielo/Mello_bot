import subprocess
import sys
from pathlib import Path

import pandas as pd

from core.manifest_generator import ManifestGenerator
from core.project_scaffolder import ProjectScaffolder


def test_generated_etl_runs_and_creates_output(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("core.project_scaffolder.BASE_DIR", tmp_path)
    manifest = ManifestGenerator.validate(
        ManifestGenerator.build_manifest_data(
            project_id="demo",
            name="Demo",
            category="geral",
            description="ETL gerado",
            project_path="projects/demo",
            entrypoint="src/main.py",
            file_id="input",
            display_name="Entrada",
            extension="csv",
            required_columns=["CNPJ"],
            outputs=["resultado.xlsx"],
        )
    )
    project_path = ProjectScaffolder.create(manifest)
    input_path = tmp_path / "input.csv"
    pd.DataFrame({"CNPJ": ["123"]}).to_csv(
        input_path,
        sep=";",
        index=False,
    )

    result = subprocess.run(
        [
            sys.executable,
            str(project_path / "src" / "main.py"),
            "--input-file",
            str(input_path),
        ],
        cwd=project_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (project_path / "data" / "output" / "resultado.xlsx").exists()
    assert "sucesso" in result.stdout


def test_generated_powerbi_template_uses_manifest_inputs_and_csv_output(
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.setattr("core.project_scaffolder.BASE_DIR", tmp_path)
    manifest = ManifestGenerator.validate(
        ManifestGenerator.build_manifest_data(
            project_id="powerbi-demo",
            name="Power BI Demo",
            category="power_bi",
            description="Dataset CSV gerado",
            project_path="projects/powerbi-demo",
            entrypoint="src/main.py",
            file_id="input",
            display_name="Entrada",
            extension="csv",
            required_columns=["Cliente"],
            outputs=["dataset.csv"],
        )
    )
    artifacts = ProjectScaffolder.create_automation_project(
        manifest,
        pattern="powerbi",
    )
    project_path = artifacts["project_path"]
    input_path = tmp_path / "input.csv"
    pd.DataFrame({"Cliente": ["A"], "Valor": [10]}).to_csv(
        input_path,
        sep=";",
        index=False,
    )

    result = subprocess.run(
        [
            sys.executable,
            str(artifacts["entrypoint_path"]),
            "--input-file",
            str(input_path),
        ],
        cwd=project_path,
        capture_output=True,
        text=True,
        check=False,
    )

    output_path = project_path / "data" / "output" / "dataset.csv"
    assert result.returncode == 0, result.stderr
    assert output_path.is_file()
    assert pd.read_csv(output_path, sep=";").iloc[0]["cliente"] == "A"


def test_generated_consolidation_template_appends_monthly_rows(
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.setattr("core.project_scaffolder.BASE_DIR", tmp_path)
    manifest_data = ManifestGenerator.build_manifest_data(
        project_id="consolidation-demo",
        name="Consolidation Demo",
        category="vendas",
        description="Consolidação mensal de vendas",
        project_path="projects/consolidation-demo",
        entrypoint="src/main.py",
        file_id="month_1",
        display_name="Mês 1",
        extension="csv",
        required_columns=["Cliente"],
        outputs=["consolidado.xlsx"],
    )
    manifest_data["required_files"][0]["cli_argument"] = "--month-1"
    manifest_data["required_files"].append(
        {
            "id": "month_2",
            "display_name": "Mês 2",
            "cli_argument": "--month-2",
            "accepted_extensions": ["csv"],
            "critical_columns": [],
            "required_columns": ["Cliente"],
        }
    )
    manifest = ManifestGenerator.validate(manifest_data)
    artifacts = ProjectScaffolder.create_automation_project(
        manifest,
        pattern="consolidation",
    )
    project_path = artifacts["project_path"]
    month_one = tmp_path / "month-one.csv"
    month_two = tmp_path / "month-two.csv"
    pd.DataFrame({"Cliente": ["A"], "Valor": [10]}).to_csv(
        month_one,
        sep=";",
        index=False,
    )
    pd.DataFrame({"Cliente": ["B"], "Valor": [20]}).to_csv(
        month_two,
        sep=";",
        index=False,
    )

    result = subprocess.run(
        [
            sys.executable,
            str(artifacts["entrypoint_path"]),
            "--month-1",
            str(month_one),
            "--month-2",
            str(month_two),
        ],
        cwd=project_path,
        capture_output=True,
        text=True,
        check=False,
    )

    output_path = project_path / "data" / "output" / "consolidado.xlsx"
    assert result.returncode == 0, result.stderr
    assert output_path.is_file()
    assert pd.read_excel(output_path)["cliente"].tolist() == ["A", "B"]


def test_reconciliation_workbook_creates_requested_named_sheets(
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.setattr("core.project_scaffolder.BASE_DIR", tmp_path)
    manifest_data = ManifestGenerator.build_manifest_data(
        project_id="reconciliation-tabs",
        name="Reconciliation Tabs",
        category="financeiro",
        description="Conciliação com abas nomeadas",
        project_path="projects/reconciliation-tabs",
        entrypoint="src/main.py",
        file_id="fs10n",
        display_name="FS10N",
        extension="xlsx",
        required_columns=["CNPJ"],
        outputs=["resultado.xlsx"],
    )
    manifest_data["required_files"][0]["cli_argument"] = "--fs10n"
    manifest_data["required_files"].append(
        {
            "id": "billing",
            "display_name": "Billing",
            "cli_argument": "--billing",
            "accepted_extensions": ["xlsx"],
            "critical_columns": [],
            "required_columns": ["CNPJ"],
        }
    )
    manifest_data["steps"] = [
        {"type": "reconcile", "key": "CNPJ"},
        {"type": "validate"},
    ]
    manifest_data["pattern"] = "reconciliation"
    manifest_data["output_mode"] = "workbook"
    manifest_data["workbook_name"] = "resultado.xlsx"
    manifest_data["workbook_sheets"] = [
        "Resumo Executivo",
        "Conciliados",
        "Divergências",
        "Apenas FS10N",
        "Apenas Billing",
    ]
    manifest = ManifestGenerator.validate(manifest_data)
    artifacts = ProjectScaffolder.create_automation_project(
        manifest,
        pattern="reconciliation",
    )
    project_path = artifacts["project_path"]
    left_input = tmp_path / "fs10n.xlsx"
    right_input = tmp_path / "billing.xlsx"
    pd.DataFrame(
        {"CNPJ": ["00000000000001", "00000000000002"], "valor": [10, 20]}
    ).to_excel(left_input, index=False)
    pd.DataFrame(
        {"CNPJ": ["00000000000001", "00000000000003"], "valor": [11, 30]}
    ).to_excel(right_input, index=False)

    result = subprocess.run(
        [
            sys.executable,
            str(artifacts["entrypoint_path"]),
            "--fs10n",
            str(left_input),
            "--billing",
            str(right_input),
        ],
        cwd=project_path,
        capture_output=True,
        text=True,
        check=False,
    )

    output_path = project_path / "data" / "output" / "resultado.xlsx"
    assert result.returncode == 0, result.stderr
    assert output_path.is_file()
    assert pd.ExcelFile(output_path).sheet_names == manifest_data["workbook_sheets"]
    assert len(pd.read_excel(output_path, sheet_name="Resumo Executivo")) == 5
    assert len(pd.read_excel(output_path, sheet_name="Conciliados")) == 1
    assert len(pd.read_excel(output_path, sheet_name="Divergências")) == 2
    assert len(pd.read_excel(output_path, sheet_name="Apenas FS10N")) == 1
    assert len(pd.read_excel(output_path, sheet_name="Apenas Billing")) == 1


def test_reconciliation_workbook_uses_prompted_tabs_and_separates_sources(
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.setattr("core.project_scaffolder.BASE_DIR", tmp_path)
    manifest_data = ManifestGenerator.build_manifest_data(
        project_id="reconciliation-tabs",
        name="Reconciliation Tabs",
        category="financeiro",
        description="Conciliação com abas revisadas",
        project_path="projects/reconciliation-tabs",
        entrypoint="src/main.py",
        file_id="fs10n",
        display_name="FS10N",
        extension="xlsx",
        required_columns=["CNPJ"],
        outputs=["resultado.xlsx"],
    )
    manifest_data["required_files"][0]["cli_argument"] = "--fs10n"
    manifest_data["required_files"].append(
        {
            "id": "billing",
            "display_name": "Billing",
            "cli_argument": "--billing",
            "accepted_extensions": ["xlsx"],
            "critical_columns": [],
            "required_columns": ["CNPJ"],
        }
    )
    manifest_data["steps"] = [
        {"type": "reconcile", "key": "CNPJ"},
        {"type": "validate"},
    ]
    manifest_data["pattern"] = "reconciliation"
    manifest_data["output_mode"] = "workbook"
    manifest_data["workbook_name"] = "resultado.xlsx"
    manifest_data["workbook_sheets"] = [
        "Resumo Executivo",
        "Conciliados",
        "Divergências",
        "Apenas FS10N",
        "Apenas Billing",
    ]
    manifest = ManifestGenerator.validate(manifest_data)
    artifacts = ProjectScaffolder.create_automation_project(
        manifest,
        pattern="reconciliation",
    )
    left_input = tmp_path / "fs10n.xlsx"
    right_input = tmp_path / "billing.xlsx"
    pd.DataFrame({"CNPJ": ["00000000000001", "00000000000002"], "valor": [10, 20]}).to_excel(
        left_input,
        index=False,
    )
    pd.DataFrame({"CNPJ": ["00000000000001", "00000000000003"], "valor": [11, 30]}).to_excel(
        right_input,
        index=False,
    )

    result = subprocess.run(
        [
            sys.executable,
            str(artifacts["entrypoint_path"]),
            "--fs10n",
            str(left_input),
            "--billing",
            str(right_input),
        ],
        cwd=artifacts["project_path"],
        capture_output=True,
        text=True,
        check=False,
    )

    output_path = artifacts["project_path"] / "data" / "output" / "resultado.xlsx"
    assert result.returncode == 0, result.stderr
    assert output_path.is_file()
    workbook = pd.ExcelFile(output_path)
    assert workbook.sheet_names == manifest_data["workbook_sheets"]
    assert len(pd.read_excel(output_path, sheet_name="Resumo Executivo")) == 5
    assert len(pd.read_excel(output_path, sheet_name="Conciliados")) == 1
    assert len(pd.read_excel(output_path, sheet_name="Divergências")) == 2
    assert len(pd.read_excel(output_path, sheet_name="Apenas FS10N")) == 1
    assert len(pd.read_excel(output_path, sheet_name="Apenas Billing")) == 1
