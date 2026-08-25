from pathlib import Path
import yaml

MANIFESTS_PATH = Path("manifests")


def load_projects() -> dict:

    projects = {}

    for manifest_file in MANIFESTS_PATH.glob("*.yaml"):

        with open(manifest_file, "r", encoding="utf-8") as file:

            manifest = yaml.safe_load(file)

            projects[manifest["id"]] = manifest

    return projects