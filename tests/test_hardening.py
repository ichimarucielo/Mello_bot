from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from core.executor import Executor
from core.manifest_loader import load_manifest
from core.models import RequiredFile
from core.output_validator import OutputValidator
from core.validator import Validator


def test_empty_csv_is_reported_clearly(tmp_path: Path):
    file_path = tmp_path / "empty.csv"
    file_path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="Arquivo sem colunas"):
        Validator.get_columns(file_path)


def test_csv_without_columns_is_rejected(tmp_path: Path):
    file_path = tmp_path / "without_columns.csv"
    file_path.write_text("\n", encoding="utf-8")

    with pytest.raises(ValueError):
        Validator.get_columns(file_path)


def test_corrupted_xlsx_is_rejected(tmp_path: Path):
    file_path = tmp_path / "corrupted.xlsx"
    file_path.write_bytes(b"not an xlsx")

    with pytest.raises(Exception):
        Validator.get_columns(file_path)


def test_invalid_manifest_reports_file_location(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("core.manifest_loader.MANIFESTS_PATH", tmp_path)
    (tmp_path / "broken.yaml").write_text("id: [", encoding="utf-8")

    with pytest.raises(ValueError, match="Manifesto inválido"):
        load_manifest("broken")


def test_output_validator_reports_declared_output_not_generated(tmp_path: Path):
    (tmp_path / "unexpected.xlsx").touch()

    result = OutputValidator.validate(
        output_folder=tmp_path,
        expected_outputs=["declared.xlsx"],
    )

    assert result["valid"] is False
    assert result["missing"] == ["declared.xlsx"]
    assert result["found"] == []


def test_executor_reports_missing_entrypoint(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("core.executor.BASE_DIR", tmp_path)
    manifest = type("ManifestStub", (), {})()
    manifest.project_path = "project"
    manifest.entrypoint = type("EntryPointStub", (), {"script": "main.py"})()
    manifest.required_files = []
    manifest.name = "Broken"

    with patch("core.executor.load_manifest", return_value=manifest):
        with pytest.raises(FileNotFoundError, match="Entrypoint não encontrado"):
            Executor.run("broken", {})


def test_executor_reports_missing_input_file(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("core.executor.BASE_DIR", tmp_path)
    project_path = tmp_path / "project"
    project_path.mkdir()
    (project_path / "main.py").touch()

    manifest = type("ManifestStub", (), {})()
    manifest.project_path = "project"
    manifest.entrypoint = type("EntryPointStub", (), {"script": "main.py"})()
    manifest.required_files = [
        RequiredFile(
            id="input",
            display_name="Input",
            accepted_extensions=["csv"],
            required_columns=[],
            cli_argument="--input",
        )
    ]
    manifest.name = "Broken"

    with patch("core.executor.load_manifest", return_value=manifest):
        with pytest.raises(FileNotFoundError, match="Arquivo de entrada"):
            Executor.run("broken", {"input": str(tmp_path / "missing.csv")})