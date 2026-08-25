from pathlib import Path

from core.identifier import Identifier
from core.file_manager import FileManager


class UploadMapper:

    @classmethod
    def map_uploaded_files(
        cls,
        project_id: str,
        uploaded_files: list
    ) -> dict:

        mapped_files = {}

        for uploaded_file in uploaded_files:

            temp_path = (
                FileManager.save_uploaded_file(
                    project_id=project_id,
                    file_id=f"temp_{uploaded_file.name}",
                    uploaded_file=uploaded_file
                )
            )

            identification = (
                Identifier.identify(
                    temp_path
                )
            )

            best_match = identification[
                "best_match"
            ]

            if not best_match:

                continue

            file_id = best_match[
                "file_id"
            ]

            mapped_files[
                file_id
            ] = {
                "uploaded_file": uploaded_file,
                "identification": identification
            }

        return mapped_files