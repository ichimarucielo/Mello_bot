from pathlib import Path
import subprocess
import sys

from core.manifest_loader import load_manifest
from core.settings import BASE_DIR


class Executor:

    @staticmethod
    def run(
        project_id: str,
        files: dict[str, str],
    ) -> None:

        manifest = load_manifest(project_id)

        project_path = (
            BASE_DIR /
            manifest.project_path
        ).resolve()

        script_path = (
            project_path /
            manifest.entrypoint.script
        )

        if not script_path.exists():

            raise FileNotFoundError(
                f"Entrypoint não encontrado: "
                f"{script_path}"
            )

        print(
            f"\nExecutando projeto: "
            f"{manifest.name}"
        )

        print(
            f"Project Path: "
            f"{project_path}"
        )

        args = [
            sys.executable,
            manifest.entrypoint.script,
        ]

        for required_file in manifest.required_files:

            cli_argument = getattr(
                required_file,
                "cli_argument",
                None,
            )

            if not cli_argument:
                continue

            args.extend(
                [
                    cli_argument,
                    files[required_file.id],
                ]
            )

        result = subprocess.run(
            args,
            cwd=project_path,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:

            raise RuntimeError(
                f"""
STDOUT:
{result.stdout}

STDERR:
{result.stderr}
"""
            )