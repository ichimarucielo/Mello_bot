from core.file_manager import FileManager
from core.identifier import Identifier


class UploadMapper:

    @classmethod
    def map_uploaded_files(
        cls,
        project_id: str,
        uploaded_files: list,
    ) -> dict:

        mapped_files = {}

        for uploaded_file in uploaded_files:

            file_name = getattr(
                uploaded_file,
                "name",
                None,
            )

            if file_name is None:

                file_name = getattr(
                    uploaded_file,
                    "filename",
                    None,
                )

            if file_name is None:

                raise ValueError(
                    "Nome do arquivo não encontrado."
                )

            if hasattr(
                uploaded_file,
                "getbuffer",
            ):

                content = (
                    uploaded_file
                    .getbuffer()
                )

            else:

                content = (
                    uploaded_file
                    .file
                    .read()
                )

            temp_path = (
                FileManager.save_uploaded_file(
                    project_id=project_id,
                    file_id=f"temp_{Path(file_name).stem}",
                    file_name=file_name,
                    content=content,
                )
            )

            identification = (
                Identifier.identify(
                    temp_path
                )
            )

            best_match = (
                identification[
                    "best_match"
                ]
            )

            if not best_match:
                continue

            file_id = (
                best_match[
                    "file_id"
                ]
            )

            FileManager.save_uploaded_file(
                project_id=project_id,
                file_id=file_id,
                file_name=file_name,
                content=content,
            )

            mapped_files[
                file_id
            ] = {
                "file_name": file_name,
                "identification": identification,
            }

        return mapped_files