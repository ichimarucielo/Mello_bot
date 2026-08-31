from pathlib import Path
import subprocess
import sys

from core.manifest_loader import load_manifest


class Executor:

    @staticmethod
    def run(
        project_id: str,
        files: dict[str, str],
    ) -> None:

        manifest = load_manifest(project_id)

        project_path = Path(
            manifest["project_path"]
        )

        script_name = manifest[
            "entrypoint"
        ]["script"]

        script_path = (
            project_path /
            script_name
        )

        if not script_path.exists():
            raise FileNotFoundError(
                f"Entrypoint não encontrado: "
                f"{script_path}"
            )

        print(
            f"\nExecutando projeto: "
            f"{manifest['name']}"
        )

        subprocess.run(
            [
                sys.executable,
                script_name,
                "--prefeitura",
                files["prefeitura"],
                "--fs10n",
                files["fs10n"],
                "--zsd008",
                files["zsd008"],
            ],
            cwd=project_path,
            check=True,
        )