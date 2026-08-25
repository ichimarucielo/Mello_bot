from pathlib import Path
import subprocess
import sys

from core.manifest_loader import load_manifest


class Executor:

    @staticmethod
    def run(project_id: str) -> None:

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

        bot_root = (
            Path(__file__)
            .resolve()
            .parent
            .parent
        )

        inputs_folder = (
            bot_root /
            "inputs" /
            project_id
        )

        prefeitura_file = (
            inputs_folder /
            "prefeitura.csv"
        )

        fs10n_file = (
            inputs_folder /
            "fs10n.xlsx"
        )

        zsd008_file = (
            inputs_folder /
            "zsd008.xlsx"
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
                str(prefeitura_file),
                "--fs10n",
                str(fs10n_file),
                "--zsd008",
                str(zsd008_file),
            ],
            cwd=project_path,
            check=True
        )