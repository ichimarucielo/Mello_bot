from pathlib import Path

import yaml

from core.models import Manifest


MANIFESTS_PATH = Path("manifests")


def load_manifest(project_id: str) -> Manifest:
    manifest_file = MANIFESTS_PATH / f"{project_id}.yaml"

    if not manifest_file.exists():
        raise FileNotFoundError(
            f"Manifest não encontrado: {manifest_file}"
        )

    try:
        with open(manifest_file, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
        return Manifest.model_validate(data)
    except Exception as error:
        raise ValueError(
            f"Manifesto inválido em {manifest_file}: {error}"
        ) from error