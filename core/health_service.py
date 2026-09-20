import sqlite3
from pathlib import Path
from typing import Any

from core.manifest_generator import ManifestGenerator
from core.manifest_loader import load_manifest
from core.settings import BASE_DIR, DATABASE_PATH, MANIFESTS_DIR


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

    @staticmethod
    def diagnose_details() -> dict[str, Any]:
        python_ok = True
        python_version = "unknown"
        try:
            import sys
            python_version = sys.version.split()[0]
        except Exception:
            python_ok = False

        manifests = ManifestGenerator.list_manifest_files()
        manifest_status = {
            "count": len(manifests),
            "valid": 0,
            "invalid": 0,
            "items": [],
        }

        for manifest_path in manifests:
            item = {
                "id": manifest_path.stem,
                "path": str(manifest_path),
                "valid": False,
                "error": None,
            }
            try:
                load_manifest(manifest_path.stem)
                item["valid"] = True
                manifest_status["valid"] += 1
            except Exception as error:
                item["error"] = str(error)
                manifest_status["invalid"] += 1
            manifest_status["items"].append(item)

        sqlite_ok = False
        sqlite_errors = None
        try:
            sqlite_ok = DATABASE_PATH.parent.exists()
            with sqlite3.connect(DATABASE_PATH) as connection:
                connection.execute("SELECT 1").fetchone()
            sqlite_ok = True
        except Exception as error:
            sqlite_errors = str(error)

        external_projects = []
        for manifest_path in manifests:
            try:
                manifest = load_manifest(manifest_path.stem)
                project_dir = (BASE_DIR / manifest.project_path).resolve()
                external_projects.append({
                    "id": manifest.id,
                    "path": str(project_dir),
                    "exists": project_dir.exists(),
                    "entrypoint_exists": (project_dir / manifest.entrypoint.script).exists(),
                    "output_folder": str(project_dir / getattr(manifest, "output_folder", "data/output")),
                })
            except Exception as error:
                external_projects.append({
                    "id": manifest_path.stem,
                    "path": str(manifest_path),
                    "exists": False,
                    "entrypoint_exists": False,
                    "output_folder": None,
                    "error": str(error),
                })

        output_status = []
        for manifest_path in manifests:
            try:
                manifest = load_manifest(manifest_path.stem)
                project_dir = (BASE_DIR / manifest.project_path).resolve()
                output_dir = project_dir / getattr(manifest, "output_folder", "data/output")
                output_status.append({
                    "project_id": manifest.id,
                    "output_dir": str(output_dir),
                    "exists": output_dir.exists(),
                    "files": [p.name for p in output_dir.glob("*") if p.is_file()] if output_dir.exists() else [],
                })
            except Exception as error:
                output_status.append({
                    "project_id": manifest_path.stem,
                    "output_dir": None,
                    "exists": False,
                    "files": [],
                    "error": str(error),
                })

        permissions = []
        for path in [BASE_DIR, MANIFESTS_DIR, DATABASE_PATH.parent, BASE_DIR / "inputs"]:
            try:
                permissions.append({
                    "path": str(path),
                    "exists": path.exists(),
                    "writable": path.exists() and (path.stat().st_mode & 0o200) != 0,
                })
            except Exception as error:
                permissions.append({
                    "path": str(path),
                    "exists": False,
                    "writable": False,
                    "error": str(error),
                })

        problems = []
        if not python_ok:
            problems.append("python_unavailable")
        if manifest_status["invalid"]:
            problems.append("invalid_manifest")
        if not sqlite_ok:
            problems.append("sqlite_unavailable")

        status = "ok"
        if problems:
            status = "warning" if problems and len(problems) < 3 else "error"

        return {
            "status": status,
            "python": {
                "ok": python_ok,
                "version": python_version,
            },
            "manifests": manifest_status,
            "sqlite": {
                "ok": sqlite_ok,
                "path": str(DATABASE_PATH),
                "error": sqlite_errors,
            },
            "projects": external_projects,
            "outputs": output_status,
            "permissions": permissions,
            "problems": problems,
        }