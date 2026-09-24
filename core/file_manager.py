from pathlib import Path

from core.settings import INPUTS_DIR
from core.storage_provider import get_storage_provider


class FileManager:

    UPLOADS_PATH = INPUTS_DIR

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

        return get_storage_provider().save_input(
            project_id=project_id,
            file_id=file_id,
            file_name=file_name,
            content=content,
        )