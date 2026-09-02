from pathlib import Path

import pandas as pd

from core.identifier import Identifier


def test_identify_matches_file_definition(tmp_path: Path):
    file_path = tmp_path / "prefeitura.csv"
    pd.DataFrame(
        columns=["Numero NF", "Numerp RPS", "CNPJ", "Valor Serviço"]
    ).to_csv(file_path, sep=";", index=False)

    result = Identifier.identify(file_path)

    assert result["best_match"] is not None
    assert result["best_match"]["project_id"] == "ia_quarteto"
    assert result["best_match"]["file_id"] == "prefeitura"
    assert result["best_match"]["confidence"] == 100.0


def test_identify_returns_no_match_when_no_projects_have_columns(tmp_path: Path):
    file_path = tmp_path / "unknown.csv"
    pd.DataFrame(columns=["unknown_column"]).to_csv(
        file_path,
        sep=";",
        index=False,
    )

    result = Identifier.identify(file_path)

    assert result["best_match"]["confidence"] == 0.0
    assert result["candidates"]
