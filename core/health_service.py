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
                "outputs_configured": False,
                "healthy": False,
                "error": None,
            }
            try:
                manifest = ManifestGenerator.validate_yaml(
                    ManifestGenerator.read_manifest_yaml(manifest_path)
                )
                item["valid"] = True
                project_path = (BASE_DIR / manifest.project_path).resolve()
                item["project_path"] = project_path.is_dir()
                item["entrypoint"] = (project_path / manifest.entrypoint.script).is_file()
                item["outputs_configured"] = bool(manifest.outputs) and all(
                    output.strip() for output in manifest.outputs
                )
                output_folder = project_path / getattr(
                    manifest,
                    "output_folder",
                    "data/output",
                )
                item["outputs"] = all(
                    (output_folder / output).exists()
                    for output in manifest.outputs
                ) and bool(manifest.outputs)
                item["healthy"] = all(
                    (
                        item["valid"],
                        item["project_path"],
                        item["entrypoint"],
                        item["outputs_configured"],
                    )
                )
                valid_count += 1
            except Exception as error:
                item["error"] = str(error)
            details.append(item)

        healthy_count = sum(item["healthy"] for item in details)
        return {
            "manifest_count": len(manifests),
            "valid_manifests": valid_count,
            "healthy_projects": healthy_count,
            "unhealthy_projects": len(manifests) - healthy_count,
            "outputs_configured": sum(item["outputs_configured"] for item in details),
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
            "healthy_projects": 0,
            "projects_needing_attention": 0,
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

        problems = []
        healthy_project_count = 0
        external_projects = []
        for manifest_path in manifests:
            try:
                manifest = load_manifest(manifest_path.stem)
                project_dir = (BASE_DIR / manifest.project_path).resolve()
                project_exists = project_dir.is_dir()
                entrypoint_exists = (
                    project_dir / manifest.entrypoint.script
                ).is_file()
                outputs_configured = bool(manifest.outputs) and all(
                    output.strip() for output in manifest.outputs
                )
                healthy = (
                    project_exists
                    and entrypoint_exists
                    and outputs_configured
                )
                if healthy:
                    healthy_project_count += 1
                if not project_exists:
                    problems.append(f"project_path_missing:{manifest.id}")
                if project_exists and not entrypoint_exists:
                    problems.append(f"entrypoint_missing:{manifest.id}")
                if not outputs_configured:
                    problems.append(f"outputs_not_configured:{manifest.id}")
                external_projects.append({
                    "id": manifest.id,
                    "path": str(project_dir),
                    "exists": project_exists,
                    "entrypoint_exists": entrypoint_exists,
                    "outputs_configured": outputs_configured,
                    "healthy": healthy,
                    "output_folder": str(project_dir / getattr(manifest, "output_folder", "data/output")),
                })
            except Exception as error:
                problems.append(f"project_manifest_invalid:{manifest_path.stem}")
                external_projects.append({
                    "id": manifest_path.stem,
                    "path": str(manifest_path),
                    "exists": False,
                    "entrypoint_exists": False,
                    "outputs_configured": False,
                    "healthy": False,
                    "output_folder": None,
                    "error": str(error),
                })
        manifest_status["healthy_projects"] = healthy_project_count
        manifest_status["projects_needing_attention"] = (
            len(manifests) - healthy_project_count
        )

        output_status = []
        for manifest_path in manifests:
            try:
                manifest = load_manifest(manifest_path.stem)
                project_dir = (BASE_DIR / manifest.project_path).resolve()
                output_dir = project_dir / getattr(manifest, "output_folder", "data/output")
                generated_outputs = [
                    output
                    for output in manifest.outputs
                    if (output_dir / output).is_file()
                ]
                output_status.append({
                    "project_id": manifest.id,
                    "output_dir": str(output_dir),
                    "exists": output_dir.exists(),
                    "configured": bool(manifest.outputs),
                    "generated": generated_outputs,
                    "missing": [
                        output
                        for output in manifest.outputs
                        if output not in generated_outputs
                    ],
                    "files": [p.name for p in output_dir.glob("*") if p.is_file()] if output_dir.exists() else [],
                })
            except Exception as error:
                output_status.append({
                    "project_id": manifest_path.stem,
                    "output_dir": None,
                    "exists": False,
                    "configured": False,
                    "generated": [],
                    "missing": [],
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

        if not python_ok:
            problems.append("python_unavailable")
        if manifest_status["invalid"]:
            problems.append("invalid_manifest")
        if not sqlite_ok:
            problems.append("sqlite_unavailable")

        critical_problems = {
            "python_unavailable",
            "invalid_manifest",
            "sqlite_unavailable",
        }
        status = (
            "error"
            if any(problem in critical_problems for problem in problems)
            else "warning"
            if problems
            else "ok"
        )

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