from typing import Any

from core.manifest_generator import ManifestGenerator
from core.settings import BASE_DIR


class HealthService:

    @staticmethod
    def diagnose() -> dict[str, Any]:
        manifests = ManifestGenerator.list_manifest_files()
        details = []
        valid_count = 0

        for manifest_path in manifests:
            item: dict[str, Any] = {
                "id": manifest_path.stem,
                "valid": False,
                "project_path": False,
                "entrypoint": False,
                "outputs": False,
                "error": None,
            }
            try:
                manifest = ManifestGenerator.validate_yaml(
                    ManifestGenerator.read_manifest_yaml(manifest_path)
                )
                item["valid"] = True
                item["project_path"] = (BASE_DIR / manifest.project_path).exists()
                project_path = (BASE_DIR / manifest.project_path).resolve()
                item["entrypoint"] = (
                    project_path / manifest.entrypoint.script
                ).exists()
                output_folder = project_path / getattr(
                    manifest,
                    "output_folder",
                    "data/output",
                )
                item["outputs"] = all(
                    (output_folder / output).exists()
                    for output in manifest.outputs
                )
                valid_count += 1
            except Exception as error:
                item["error"] = str(error)
            details.append(item)

        return {
            "manifest_count": len(manifests),
            "valid_manifests": valid_count,
            "projects_found": sum(item["project_path"] for item in details),
            "valid_paths": sum(item["project_path"] for item in details),
            "entrypoints_found": sum(item["entrypoint"] for item in details),
            "accessible_outputs": sum(item["outputs"] for item in details),
            "details": details,
        }