from pathlib import Path
from unittest.mock import patch

import pytest

from core.enums import ExecutionStatus
from core.exceptions import ProjectNotFoundError
from core.models import ExecutionResult
from core.orchestrator import Orchestrator
from core.settings import INPUTS_DIR


def test_list_projects_returns_loaded_manifests():
    projects = Orchestrator.list_projects()

    assert {
        "antifraude",
        "ia_quarteto",
    }.issubset({project.id for project in projects})


def test_get_project_raises_domain_error_for_unknown_project():
    with pytest.raises(ProjectNotFoundError):
        Orchestrator.get_project("unknown_project")


def test_build_project_files_uses_manifest_extensions():
    project = Orchestrator.get_project("ia_quarteto")

    files = Orchestrator.build_project_files("ia_quarteto", project)

    assert files == {
        "prefeitura": str(INPUTS_DIR / "ia_quarteto" / "prefeitura.csv"),
        "fs10n": str(INPUTS_DIR / "ia_quarteto" / "fs10n.xlsx"),
        "zsd008": str(INPUTS_DIR / "ia_quarteto" / "zsd008.xlsx"),
    }


def test_run_project_maps_executes_validates_and_logs():
    execution_result = ExecutionResult(
        execution_id="",
        project_id="ia_quarteto",
        status=ExecutionStatus.SUCCESS,
        duration_seconds=1.25,
    )
    mapped_files = {"prefeitura": {}}
    output_result = {
        "found": [{"name": "Report_Faturamento.xlsx"}],
        "missing": ["Check_Faturamento.xlsx"],
    }

    with patch(
        "core.orchestrator.UploadMapper.map_uploaded_files",
        return_value=mapped_files,
    ) as map_files, patch(
        "core.orchestrator.Executor.run",
        return_value=execution_result,
    ) as run_executor, patch(
        "core.orchestrator.OutputValidator.validate",
        return_value=output_result,
    ) as validate_outputs, patch(
        "core.orchestrator.ExecutionLogger.save",
    ) as save_execution:
        result = Orchestrator.run_project(
            project_id="ia_quarteto",
            uploaded_files=["uploaded-file"],
        )

    assert result.status == "success"
    assert result.mapped_files == ["prefeitura"]
    assert result.outputs == ["Report_Faturamento.xlsx"]
    map_files.assert_called_once()
    run_executor.assert_called_once()
    validate_outputs.assert_called_once()
    save_execution.assert_called_once_with(execution_result)
