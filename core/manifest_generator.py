from pathlib import Path
from typing import Any
from datetime import datetime
import re
import unicodedata

import yaml

from core.models import Manifest
from core.settings import MANIFESTS_DIR
from core.validator import Validator


class ManifestGenerator:

    @staticmethod
    def suggest(
        file_name: str,
        columns: list[str],
    ) -> dict[str, str]:
        source_name = Path(file_name).stem
        normalized_name = unicodedata.normalize(
            "NFKD",
            source_name,
        ).encode("ascii", "ignore").decode("ascii")
        project_id = re.sub(
            r"[^a-z0-9]+",
            "_",
            normalized_name.lower(),
        ).strip("_") or "novo_projeto"
        project_name = " ".join(
            part.capitalize()
            for part in re.split(r"[_\-\s]+", source_name)
            if part
        ) or "Novo Projeto"

        searchable_text = " ".join(columns).lower()
        category = "geral"
        for candidate, keywords in {
            "financeiro": ("valor", "montante", "conta", "fatura"),
            "faturamento": ("nota", "rps", "billing", "nf"),
            "estoque": ("estoque", "sku", "quantidade"),
            "clientes": ("cliente", "cnpj", "email"),
        }.items():
            if any(keyword in searchable_text for keyword in keywords):
                category = candidate
                break

        return {
            "project_id": project_id,
            "name": project_name,
            "category": category,
            "description": f"ETL gerado a partir do arquivo {file_name}.",
            "display_name": project_name,
        }

    @staticmethod
    def list_manifest_files() -> list[Path]:
        MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
        return sorted(MANIFESTS_DIR.glob("*.yaml"))

    @staticmethod
    def read_manifest_yaml(manifest_path: Path) -> str:
        return manifest_path.read_text(encoding="utf-8")

    @staticmethod
    def extract_columns(
        file_path: Path,
    ) -> list[str]:
        return Validator.get_columns(file_path)

    @staticmethod
    def build_manifest_data(
        project_id: str,
        name: str,
        category: str,
        description: str,
        project_path: str,
        entrypoint: str,
        file_id: str,
        display_name: str,
        extension: str,
        required_columns: list[str],
        outputs: list[str],
    ) -> dict[str, Any]:
        return {
            "id": project_id,
            "name": name,
            "category": category,
            "description": description,
            "project_path": project_path,
            "timeout_seconds": 1800,
            "entrypoint": {"script": entrypoint},
            "required_files": [
                {
                    "id": file_id,
                    "display_name": display_name,
                    "cli_argument": "--input-file",
                    "accepted_extensions": [extension],
                    "required_columns": required_columns,
                }
            ],
            "outputs": outputs,
            "tags": [],
        }

    @staticmethod
    def validate(data: dict[str, Any]) -> Manifest:
        return Manifest.model_validate(data)

    @staticmethod
    def validate_yaml(manifest_yaml: str) -> Manifest:
        return ManifestGenerator.validate(yaml.safe_load(manifest_yaml))

    @staticmethod
    def to_yaml(manifest: Manifest) -> str:
        return yaml.safe_dump(
            manifest.model_dump(mode="json"),
            allow_unicode=True,
            sort_keys=False,
        )

    @staticmethod
    def save(manifest: Manifest) -> Path:
        MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
        manifest_path = MANIFESTS_DIR / f"{manifest.id}.yaml"

        if manifest_path.exists():
            raise FileExistsError(
                f"Manifest já existe: {manifest_path}"
            )

        manifest_path.write_text(
            ManifestGenerator.to_yaml(manifest),
            encoding="utf-8",
        )
        return manifest_path

    @staticmethod
    def save_versioned(manifest: Manifest) -> Path:
        MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
        manifest_path = MANIFESTS_DIR / f"{manifest.id}.yaml"
        if manifest_path.exists():
            version_path = MANIFESTS_DIR / (
                f"{manifest.id}_{datetime.now():%Y%m%d_%H%M%S}.yaml"
            )
            version_path.write_text(
                ManifestGenerator.read_manifest_yaml(manifest_path),
                encoding="utf-8",
            )
        manifest_path.write_text(
            ManifestGenerator.to_yaml(manifest),
            encoding="utf-8",
        )
        return manifest_path

    @staticmethod
    def list_versions(manifest_id: str) -> list[Path]:
        return sorted(
            MANIFESTS_DIR.glob(f"{manifest_id}_*.yaml"),
            reverse=True,
        )

    @staticmethod
    def delete(manifest: Manifest) -> list[Path]:
        deleted_paths = []
        manifest_path = MANIFESTS_DIR / f"{manifest.id}.yaml"

        if manifest_path.exists():
            manifest_path.unlink()
            deleted_paths.append(manifest_path)

        for version_path in ManifestGenerator.list_versions(manifest.id):
            version_path.unlink()
            deleted_paths.append(version_path)

        return deleted_paths
