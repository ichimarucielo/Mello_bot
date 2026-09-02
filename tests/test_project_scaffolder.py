from pathlib import Path

from core.manifest_generator import ManifestGenerator
from core.project_scaffolder import ProjectScaffolder


def test_create_generates_project_structure(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("core.project_scaffolder.BASE_DIR", tmp_path)
    manifest = ManifestGenerator.validate(
        ManifestGenerator.build_manifest_data(
            project_id="demo",
            name="Demo",
            category="geral",
            description="Projeto de teste",
            project_path="projects/demo",
            entrypoint="src/main.py",
            file_id="input",
            display_name="Entrada",
            extension="csv",
            required_columns=["CNPJ"],
            outputs=[],
        )
    )

    project_path = ProjectScaffolder.create(manifest)

    assert project_path == tmp_path / "projects" / "demo"
    assert (project_path / "src" / "main.py").exists()
    assert (project_path / "data" / "input").is_dir()
    assert (project_path / "data" / "output").is_dir()