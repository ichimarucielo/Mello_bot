from pathlib import Path

import pytest

from core.manifest_loader import load_manifest
from core.models import Manifest


def test_load_manifest_returns_typed_manifest():
    manifest = load_manifest("ia_quarteto")

    assert isinstance(manifest, Manifest)
    assert manifest.id == "ia_quarteto"
    assert manifest.entrypoint.script == "main.py"
    assert {file.id for file in manifest.required_files} == {
        "prefeitura",
        "fs10n",
        "zsd008",
    }


def test_load_manifest_raises_for_unknown_project():
    with pytest.raises(FileNotFoundError):
        load_manifest("project_that_does_not_exist")
