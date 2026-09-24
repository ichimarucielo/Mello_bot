from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

from core.settings import INPUTS_DIR, OUTPUTS_DIR


class StorageProvider(Protocol):
    name: str

    def save_input(
        self,
        project_id: str,
        file_id: str,
        file_name: str,
        content: bytes,
    ) -> Path:
        ...

    def save_output(
        self,
        project_id: str,
        file_name: str,
        content: bytes,
    ) -> Path:
        ...

    def list_outputs(self, project_id: str) -> list[Path]:
        ...


class LocalStorageProvider:
    name = "local"

    def save_input(
        self,
        project_id: str,
        file_id: str,
        file_name: str,
        content: bytes,
    ) -> Path:
        folder = INPUTS_DIR / project_id
        folder.mkdir(parents=True, exist_ok=True)
        suffix = Path(file_name).suffix.lower()
        target = folder / f"{file_id}{suffix}"
        target.write_bytes(content)
        return target

    def save_output(
        self,
        project_id: str,
        file_name: str,
        content: bytes,
    ) -> Path:
        folder = OUTPUTS_DIR / project_id
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / Path(file_name).name
        target.write_bytes(content)
        return target

    def list_outputs(self, project_id: str) -> list[Path]:
        folder = OUTPUTS_DIR / project_id
        return sorted(path for path in folder.glob("*") if path.is_file())


class SharePointStorageProvider:
    name = "sharepoint"

    def __init__(self) -> None:
        raise RuntimeError(
            "SharePointStorageProvider requer a integração Microsoft Graph configurada."
        )


def get_storage_provider() -> StorageProvider:
    backend = os.getenv("STORAGE_BACKEND", "local").strip().lower()
    if backend == "local":
        return LocalStorageProvider()
    if backend == "sharepoint":
        return SharePointStorageProvider()
    raise ValueError(f"STORAGE_BACKEND não suportado: {backend}")