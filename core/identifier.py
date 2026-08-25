from pathlib import Path

from core.registry import load_projects
from core.validator import Validator


class Identifier:

    @classmethod
    def identify(
        cls,
        file_path: Path
    ) -> dict:

        file_columns = [
            str(column).strip().upper()
            for column in Validator.get_columns(
                file_path
            )
        ]

        candidates = []

        projects = load_projects()

        for project in projects.values():

            for file_definition in (
                project["required_files"]
            ):

                required_columns = [
                    str(column).strip().upper()
                    for column in file_definition.get(
                        "required_columns",
                        []
                    )
                ]

                if not required_columns:

                    continue

                matched_columns = sum(
                    1
                    for column in required_columns
                    if column in file_columns
                )

                confidence = round(
                    (
                        matched_columns
                        / len(required_columns)
                    ) * 100,
                    2
                )

                candidates.append(
                    {
                        "file_id": file_definition[
                            "id"
                        ],
                        "display_name": file_definition[
                            "display_name"
                        ],
                        "confidence": confidence,
                        "matched_columns": matched_columns,
                        "required_columns": len(
                            required_columns
                        )
                    }
                )

        candidates.sort(
            key=lambda x: x["confidence"],
            reverse=True
        )

        best_match = (
            candidates[0]
            if candidates
            else None
        )

        return {
            "best_match": best_match,
            "candidates": candidates
        }