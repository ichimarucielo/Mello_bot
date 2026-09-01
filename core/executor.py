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

        manifest = load_manifest(
            project_id
        )

        bot_root = (
            Path(__file__)
            .resolve()
            .parent
            .parent
        )

        project_path = (
            bot_root /
            manifest["project_path"]
        ).resolve()

        script_name = (
            manifest["entrypoint"][
                "script"
            ]
        )

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

        print(
            f"Project Path: "
            f"{project_path}"
        )

        args = [
            sys.executable,
            script_name,
        ]

        for required_file in manifest.get(
            "required_files",
            [],
        ):

            cli_argument = (
                required_file.get(
                    "cli_argument"
                )
            )

            if not cli_argument:
                continue

            file_id = (
                required_file["id"]
            )

            args.extend(
                [
                    cli_argument,
                    files[file_id],
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