from pathlib import Path

import pandas as pd

from core.column_normalizer import normalize_column
from core.models import RequiredFile


class Validator:

    @staticmethod
    def get_columns(file_path: Path) -> list:
        extension = file_path.suffix.lower()

        if extension == ".csv":

            try:
                df = pd.read_csv(
                    file_path,
                    nrows=0,
                    encoding="utf-8",
                    sep=";"
                )

            except UnicodeDecodeError:

                df = pd.read_csv(
                    file_path,
                    nrows=0,
                    encoding="latin1",
                    sep=";"
                )

            except pd.errors.EmptyDataError as error:
                raise ValueError(
                    f"Arquivo sem colunas: {file_path}"
                ) from error

            columns = list(df.columns)
            if not columns:
                raise ValueError(
                    f"Arquivo sem colunas: {file_path}"
                )

            return columns

        if extension == ".xlsx":

            df = pd.read_excel(
                file_path,
                nrows=0
            )

            columns = list(df.columns)
            if not columns:
                raise ValueError(
                    f"Arquivo sem colunas: {file_path}"
                )

            return columns

        raise ValueError(
            f"Extensão não suportada: {extension}"
        )

    @classmethod
    def validate_columns(
        cls,
        file_path: Path,
        required_columns: list[str]
    ) -> dict:

        original_columns = cls.get_columns(file_path)

        normalized_columns = {
            normalize_column(column)
            for column in original_columns
        }

        missing_columns = []

        for column in required_columns:

            normalized_required = normalize_column(column)

            if normalized_required not in normalized_columns:
                missing_columns.append(column)

        valid = len(missing_columns) == 0

        score = (
            100
            if valid
            else int(
                (
                    (
                        len(required_columns)
                        - len(missing_columns)
                    )
                    / len(required_columns)
                ) * 100
            )
        )

        return {
            "valid": valid,
            "score": score,
            "columns_found": original_columns,
            "missing_columns": missing_columns
        }

    @classmethod
    def validate_file(
        cls,
        file_path: Path,
        file_definition: RequiredFile
    ) -> dict:

        validation_result = cls.validate_columns(
            file_path=file_path,
            required_columns=file_definition.required_columns
        )
        critical_result = (
            cls.validate_columns(
                file_path=file_path,
                required_columns=file_definition.critical_columns,
            )
            if file_definition.critical_columns
            else {
                "valid": True,
                "score": 100,
                "missing_columns": [],
            }
        )

        return {
            "file_id": file_definition.id,
            "display_name": file_definition.display_name,
            "confidence_score": min(
                validation_result["score"],
                critical_result["score"],
            ),
            "critical_columns": file_definition.critical_columns,
            "missing_critical_columns": critical_result["missing_columns"],
            "critical_columns_valid": critical_result["valid"],
            **validation_result
        }