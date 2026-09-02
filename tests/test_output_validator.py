from pathlib import Path

from core.output_validator import OutputValidator


def test_validate_reports_found_and_missing_outputs(tmp_path: Path):
    (tmp_path / "created.xlsx").write_bytes(b"output")

    result = OutputValidator.validate(
        output_folder=tmp_path,
        expected_outputs=["created.xlsx", "missing.xlsx"],
    )

    assert result["valid"] is False
    assert result["found"] == [
        {"name": "created.xlsx", "path": tmp_path / "created.xlsx"}
    ]
    assert result["missing"] == ["missing.xlsx"]


def test_validate_returns_valid_when_all_outputs_exist(tmp_path: Path):
    (tmp_path / "one.xlsx").touch()
    (tmp_path / "two.xlsx").touch()

    result = OutputValidator.validate(
        output_folder=tmp_path,
        expected_outputs=["one.xlsx", "two.xlsx"],
    )

    assert result["valid"] is True
    assert len(result["found"]) == 2
    assert result["missing"] == []
