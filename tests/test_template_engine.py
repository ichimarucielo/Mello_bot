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
