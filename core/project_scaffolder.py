from pathlib import Path
import shutil

from core.models import Manifest
from core.settings import BASE_DIR


class ProjectScaffolder:

    @staticmethod
    def create(manifest: Manifest) -> Path:
        project_folder = (BASE_DIR / manifest.project_path).resolve()
        project_folder.mkdir(parents=True, exist_ok=True)

        (project_folder / "data" / "input").mkdir(
            parents=True,
            exist_ok=True,
        )
        (project_folder / "data" / "output").mkdir(
            parents=True,
            exist_ok=True,
        )

        entrypoint = project_folder / manifest.entrypoint.script
        entrypoint.parent.mkdir(parents=True, exist_ok=True)

        if not entrypoint.exists():
            entrypoint.write_text(
                """from pathlib import Path\n\n\ndef main() -> None:\n    # TODO: implement the ETL generated from the manifest.\n    pass\n\n\nif __name__ == \"__main__\":\n    main()\n""",
                encoding="utf-8",
            )

        return project_folder

    @staticmethod
    def delete(manifest: Manifest) -> Path:
        project_folder = (BASE_DIR / manifest.project_path).resolve()
        base_folder = BASE_DIR.resolve()

        if project_folder == base_folder:
            raise ValueError("O diretório raiz não pode ser removido.")

        if project_folder.exists():
            if not project_folder.is_dir():
                raise ValueError("O caminho do projeto não é um diretório.")
            shutil.rmtree(project_folder)

        return project_folder
