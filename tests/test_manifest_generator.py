from pathlib import Path

import pandas as pd
import pytest

from core.manifest_generator import ManifestGenerator
from core.models import Manifest


def test_extract_columns_from_csv(tmp_path: Path):
    file_path = tmp_path / "sample.csv"
    pd.DataFrame(columns=["CNPJ", "Valor"]).to_csv(
        file_path,
        sep=";",
        index=False,
    )

    assert ManifestGenerator.extract_columns(file_path) == ["CNPJ", "Valor"]


def test_build_validate_and_serialize_manifest():
    data = ManifestGenerator.build_manifest_data(
        project_id="demo",
        name="Demo",
        category="geral",
        description="Projeto de teste",
        project_path="../demo",
        entrypoint="main.py",
        file_id="input",
        display_name="Entrada",
        extension="csv",
        required_columns=["CNPJ"],
        outputs=["resultado.xlsx"],
    )

    manifest = ManifestGenerator.validate(data)
    yaml_text = ManifestGenerator.to_yaml(manifest)

    assert isinstance(manifest, Manifest)
    assert "id: demo" in yaml_text
    assert "required_columns:" in yaml_text
    assert "- CNPJ" in yaml_text


def test_validate_accepts_pipeline_v2_and_normalizes_to_steps():
    data = ManifestGenerator.build_manifest_data(
        project_id="v2",
        name="V2",
        category="geral",
        description="Pipeline V2",
        project_path="projects/v2",
        entrypoint="main.py",
        file_id="input",
        display_name="Entrada",
        extension="csv",
        required_columns=["documento"],
        outputs=["resultado.xlsx"],
    )
    data["pipeline"] = {
        "operations": [
            {"operation": "normalize"},
            {"operation": "aggregate", "parameters": {"group_by": "documento"}},
        ]
    }

    manifest = ManifestGenerator.validate(data)

    assert [step.operation for step in manifest.steps] == ["normalize", "aggregate"]
    assert manifest.pipeline is not None
    assert len(manifest.pipeline.operations) == 2


def test_save_does_not_overwrite_existing_manifest(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("core.manifest_generator.MANIFESTS_DIR", tmp_path)
    manifest = ManifestGenerator.validate(
        ManifestGenerator.build_manifest_data(
            project_id="demo",
            name="Demo",
            category="geral",
            description="Projeto de teste",
            project_path="../demo",
            entrypoint="main.py",
            file_id="input",
            display_name="Entrada",
            extension="csv",
            required_columns=["CNPJ"],
            outputs=["resultado.xlsx"],
        )
    )

    ManifestGenerator.save(manifest)

    with pytest.raises(FileExistsError):
        ManifestGenerator.save(manifest)


def test_xls_extension_is_preserved_in_manifest():
    data = ManifestGenerator.build_manifest_data(
        project_id="legacy",
        name="Legacy",
        category="geral",
        description="Projeto de teste",
        project_path="projects/legacy",
        entrypoint="src/main.py",
        file_id="input",
        display_name="Entrada",
        extension="xls",
        required_columns=["CNPJ"],
        outputs=[],
    )

    manifest = ManifestGenerator.validate(data)

    assert manifest.required_files[0].accepted_extensions == ["xls"]
    assert manifest.entrypoint.script == "src/main.py"


def test_suggest_builds_manifest_fields_from_file_structure():
    suggestions = ManifestGenerator.suggest(
        "FS10N.xlsx",
        ["Centro de Custo", "Montante", "Conta"],
    )

    assert suggestions == {
        "project_id": "fs10n",
        "name": "Fs10n",
        "category": "financeiro",
        "description": "ETL gerado a partir do arquivo FS10N.xlsx.",
        "display_name": "Fs10n",
    }
