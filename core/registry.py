from core.manifest_loader import load_manifest
from core.models import Manifest
from core.settings import MANIFESTS_DIR


def load_projects() -> dict[str, Manifest]:
    projects: dict[str, Manifest] = {}

    for manifest_file in MANIFESTS_DIR.glob("*.yaml"):
        project_id = manifest_file.stem

        manifest = load_manifest(project_id)

        projects[manifest.id] = manifest

    return projects