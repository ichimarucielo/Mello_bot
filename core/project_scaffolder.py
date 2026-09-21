from pathlib import Path
import shutil

from core.models import Manifest
from core.settings import BASE_DIR
from core.template_engine import TemplateEngine


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
                TemplateEngine.render_main(manifest),
                encoding="utf-8",
            )

        return project_folder

    @staticmethod
    def create_automation_project(
        manifest: Manifest,
        pattern: str = "generic",
    ) -> dict[str, Path]:
        project_folder = ProjectScaffolder.create(manifest)
        entrypoint = project_folder / manifest.entrypoint.script
        manifest_path = project_folder / "manifest.yaml"
        readme_path = project_folder / "README.md"

        entrypoint.write_text(
            TemplateEngine.render_pattern_main(manifest, pattern),
            encoding="utf-8",
        )
        manifest_path.write_text(
            TemplateEngine.render_manifest(manifest),
            encoding="utf-8",
        )
        readme_path.write_text(
            TemplateEngine.render_readme(manifest),
            encoding="utf-8",
        )
        return {
            "project_path": project_folder,
            "manifest_path": manifest_path,
            "readme_path": readme_path,
            "entrypoint_path": entrypoint,
        }

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
