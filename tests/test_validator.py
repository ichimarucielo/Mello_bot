from pathlib import Path

import pandas as pd
import pytest

from core.models import RequiredFile
from core.validator import Validator


def test_validate_csv_columns_and_normalization(tmp_path: Path):
    file_path = tmp_path / "input.csv"
    pd.DataFrame(
        columns=[" Numero NF ", "CNPJ", "Valor Serviço"]
    ).to_csv(file_path, sep=";", index=False)

    result = Validator.validate_columns(
        file_path=file_path,
        required_columns=["Numero NF", "CNPJ", "Valor Serviço"],
    )

    assert result["valid"] is True
    assert result["score"] == 100
    assert result["missing_columns"] == []


def test_validate_xlsx_reports_missing_columns(tmp_path: Path):
    file_path = tmp_path / "input.xlsx"
    pd.DataFrame(columns=["Child", "MID"]).to_excel(file_path, index=False)

    result = Validator.validate_file(
        file_path=file_path,
        file_definition=RequiredFile(
            id="base_antifraude",
            display_name="Base Antifraude",
            accepted_extensions=["xlsx"],
            required_columns=["Child", "MID", "Total Amount Due"],
        ),
    )

    assert result["valid"] is False
    assert result["score"] == 66
    assert result["missing_columns"] == ["Total Amount Due"]


def test_validate_file_reports_critical_columns_and_confidence(tmp_path: Path):
    file_path = tmp_path / "fbl5n.xlsx"
    pd.DataFrame(columns=["Conta", "Nº documento"]).to_excel(
        file_path,
        index=False,
    )

    result = Validator.validate_file(
        file_path=file_path,
        file_definition=RequiredFile(
            id="fbl5n_compensada",
            display_name="FBL5N Compensada",
            accepted_extensions=["xlsx"],
            critical_columns=["Conta", "Nº documento", "Valor Aging"],
            required_columns=["Conta", "Nº documento"],
        ),
    )

    assert result["confidence_score"] == 66
    assert result["critical_columns_valid"] is False
    assert result["missing_critical_columns"] == ["Valor Aging"]


def test_validate_rejects_unsupported_extension(tmp_path: Path):
    file_path = tmp_path / "input.txt"
    file_path.write_text("column\nvalue\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Extensão não suportada"):
        Validator.get_columns(file_path)
