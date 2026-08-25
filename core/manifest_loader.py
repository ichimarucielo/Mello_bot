from pathlib import Path
import yaml


MANIFESTS_PATH = Path("manifests")


def load_manifest(project_id: str) -> dict:
    manifest_file = MANIFESTS_PATH / f"{project_id}.yaml"

    if not manifest_file.exists():
        raise FileNotFoundError(
            f"Manifest não encontrado: {manifest_file}"
        )

    with open(manifest_file, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)