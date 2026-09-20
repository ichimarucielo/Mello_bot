import subprocess
import sys
from datetime import datetime
from pathlib import Path

from core.enums import ExecutionStatus
from core.exceptions import TimeoutExecutionError
from core.logger import log_execution_failure, log_execution_start, log_execution_success
from core.manifest_loader import load_manifest
from core.models import ExecutionResult
from core.settings import BASE_DIR


class Executor:

    @staticmethod
    def run(
        project_id: str,
        files: dict[str, str],
    ) -> ExecutionResult:

        started_at = datetime.now()
        manifest = load_manifest(project_id)
        timeout_seconds = getattr(manifest, "timeout_seconds", 1800)

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
                f"Entrypoint não encontrado: {script_path}"
            )

        log_execution_start(
            execution_id=None,
            project_id=project_id,
            duration=0,
            uploaded_files=list(files.keys()),
            status="running",
            timeout_seconds=timeout_seconds,
        )

        args = [
            sys.executable,
            manifest.entrypoint.script,
        ]

        for required_file in manifest.required_files:
            cli_argument = required_file.cli_argument
            if not cli_argument:
                continue

            file_path = files.get(required_file.id)
            if not file_path:
                raise ValueError(
                    f"Arquivo obrigatório não mapeado: {required_file.id}"
                )

            if not Path(file_path).exists():
                raise FileNotFoundError(
                    f"Arquivo de entrada não encontrado para {required_file.id}: {file_path}"
                )

            args.extend([
                cli_argument,
                file_path,
            ])

        try:
            result = subprocess.run(
                args,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as error:
            duration_seconds = round((datetime.now() - started_at).total_seconds(), 2)
            log_execution_failure(
                execution_id=None,
                project_id=project_id,
                duration=duration_seconds,
                uploaded_files=list(files.keys()),
                exception=TimeoutExecutionError(project_id, timeout_seconds),
                status="timeout",
            )
            raise TimeoutExecutionError(project_id, timeout_seconds) from error

        duration_seconds = round((datetime.now() - started_at).total_seconds(), 2)

        if result.returncode != 0:
            error_message = f"""
STDOUT:
{result.stdout}

STDERR:
{result.stderr}
"""
            log_execution_failure(
                execution_id=None,
                project_id=project_id,
                duration=duration_seconds,
                uploaded_files=list(files.keys()),
                exception=error_message,
                status="failed",
            )
            return ExecutionResult(
                execution_id="",
                project_id=project_id,
                status=ExecutionStatus.FAILED,
                duration_seconds=duration_seconds,
                error_message=error_message,
            )

        log_execution_success(
            execution_id=None,
            project_id=project_id,
            duration=duration_seconds,
            uploaded_files=list(files.keys()),
            outputs=[],
            status="success",
        )

        return ExecutionResult(
            execution_id="",
            project_id=project_id,
            status=ExecutionStatus.SUCCESS,
            duration_seconds=duration_seconds,
        )