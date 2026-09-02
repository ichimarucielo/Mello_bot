from pathlib import Path

import pytest

from core.manifest_generator import ManifestGenerator
from core.orchestrator import Orchestrator


def test_delete_project_removes_manifest_versions_and_project_folder(
    tmp_path: Path,
    monkeypatch,
):
    manifests_path = tmp_path / "manifests"
    project_root = tmp_path / "projects"
    monkeypatch.setattr("core.manifest_generator.MANIFESTS_DIR", manifests_path)
    monkeypatch.setattr("core.project_scaffolder.BASE_DIR", tmp_path)
    monkeypatch.setattr("core.orchestrator.BASE_DIR", tmp_path)
    monkeypatch.setattr(
        "core.orchestrator.load_projects",
        lambda: {"demo": manifest},
    )

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
    manifests_path.mkdir()
    (manifests_path / "demo.yaml").write_text("manifest", encoding="utf-8")
    (manifests_path / "demo_20260902_100000.yaml").write_text(
        "version", encoding="utf-8"
    )
    (project_root / "demo" / "src").mkdir(parents=True)
    (project_root / "demo" / "src" / "main.py").write_text("pass")

    deleted_path = Orchestrator.delete_project("demo")

    assert deleted_path == project_root / "demo"
    assert not deleted_path.exists()
    assert not (manifests_path / "demo.yaml").exists()
    assert not (manifests_path / "demo_20260902_100000.yaml").exists()


def test_delete_project_rejects_repository_root(monkeypatch):
    manifest = ManifestGenerator.validate(
        ManifestGenerator.build_manifest_data(
            project_id="root",
            name="Root",
            category="geral",
            description="Projeto de teste",
            project_path=".",
            entrypoint="main.py",
            file_id="input",
            display_name="Entrada",
            extension="csv",
            required_columns=["CNPJ"],
            outputs=[],
        )
    )
    monkeypatch.setattr(
        "core.orchestrator.load_projects",
        lambda: {"root": manifest},
    )

    with pytest.raises(ValueError, match="raiz"):
        Orchestrator.delete_project("root")