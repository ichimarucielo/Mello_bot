from pathlib import Path

import pandas as pd


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

            return list(df.columns)

        if extension == ".xlsx":

            df = pd.read_excel(
                file_path,
                nrows=0
            )

            return list(df.columns)

        raise ValueError(
            f"Extensão não suportada: {extension}"
        )

    @classmethod
    def validate_columns(
        cls,
        file_path: Path,
        required_columns: list[str]
    ) -> dict:

        columns = [
            str(column).strip().upper()
            for column in cls.get_columns(file_path)
        ]

        required_columns = [
            str(column).strip().upper()
            for column in required_columns
        ]

        missing_columns = []

        for column in required_columns:

            if column not in columns:

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
            "columns_found": columns,
            "missing_columns": missing_columns
        }

    @classmethod
    def validate_file(
        cls,
        file_path: Path,
        file_definition: dict
    ) -> dict:

        required_columns = (
            file_definition.get(
                "required_columns",
                []
            )
        )

        validation_result = cls.validate_columns(
            file_path=file_path,
            required_columns=required_columns
        )

        return {
            "file_id": file_definition["id"],
            "display_name": file_definition["display_name"],
            **validation_result
        }