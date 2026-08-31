from pathlib import Path


class FileManager:

    UPLOADS_PATH = Path("inputs")

    @classmethod
    def ensure_folders(
        cls,
    ) -> None:

        cls.UPLOADS_PATH.mkdir(
            parents=True,
            exist_ok=True,
        )

    @classmethod
    def save_uploaded_file(
        cls,
        project_id: str,
        file_id: str,
        file_name: str,
        content: bytes,
    ) -> Path:

        project_folder = (
            cls.UPLOADS_PATH /
            project_id
        )

        project_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        file_extension = (
            file_name.split(".")[-1]
        ).lower()

        target_file = (
            project_folder /
            f"{file_id}.{file_extension}"
        )

        with open(
            target_file,
            "wb",
        ) as file:

            file.write(content)

        return target_file