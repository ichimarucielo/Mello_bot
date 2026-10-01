from pathlib import Path
from typing import Any, Optional
import logging
from core.executor import Executor
from core.models import Manifest, RunProjectResult, ExecutionContext
from core.output_validator import OutputValidator
from core.registry import load_projects
from core.settings import BASE_DIR, INPUTS_DIR
from core.upload_mapper import UploadMapper
from core.exceptions import ProjectNotFoundError, FileProcessingError
from core.enums import ExecutionStatus
from core.execution_logger import ExecutionLogger
from core.file_manager import FileManager
from core.validator import Validator
from core.manifest_generator import ManifestGenerator
from core.project_scaffolder import ProjectScaffolder
from core.health_service import HealthService
from core.storage_provider import get_storage_provider
from datetime import datetime
from core.template_engine import TemplateEngine



logger = logging.getLogger(__name__)

class Orchestrator:

    @staticmethod
    def extract_columns(file_path: Path) -> list[str]:
        return ManifestGenerator.extract_columns(file_path)

    @staticmethod
    def suggest_manifest(file_name: str, columns: list[str]) -> dict[str, str]:
        return ManifestGenerator.suggest(file_name, columns)

    @staticmethod
    def build_manifest_data(**kwargs: Any) -> dict[str, Any]:
        return ManifestGenerator.build_manifest_data(**kwargs)

    @staticmethod
    def validate_manifest(data: dict[str, Any]) -> Manifest:
        return ManifestGenerator.validate(data)

    @staticmethod
    def validate_manifest_yaml(manifest_yaml: str) -> Manifest:
        return ManifestGenerator.validate_yaml(manifest_yaml)

    @staticmethod
    def manifest_to_yaml(manifest: Manifest) -> str:
        return ManifestGenerator.to_yaml(manifest)

    @staticmethod
    def save_manifest(manifest: Manifest) -> Path:
        return ManifestGenerator.save(manifest)

    @staticmethod
    def save_versioned_manifest(manifest: Manifest) -> Path:
        return ManifestGenerator.save_versioned(manifest)

    @staticmethod
    def list_manifest_versions(manifest_id: str) -> list[Path]:
        return ManifestGenerator.list_versions(manifest_id)

    @staticmethod
    def diagnose() -> dict[str, Any]:
        return HealthService.diagnose()

    @staticmethod
    def list_manifest_files() -> list[Path]:
        return ManifestGenerator.list_manifest_files()

    @staticmethod
    def read_manifest_yaml(manifest_path: Path) -> str:
        return ManifestGenerator.read_manifest_yaml(manifest_path)

    @staticmethod
    def create_project_structure(manifest: Manifest) -> Path:
        return ProjectScaffolder.create(manifest)

    @staticmethod
    def create_project(manifest: Manifest) -> tuple[Path, Path]:
        manifest_path = ManifestGenerator.save(manifest)
        project_path = ProjectScaffolder.create(manifest)
        return manifest_path, project_path

    @classmethod
    def delete_project(cls, project_id: str) -> Path:
        project = cls.get_project(project_id)
        project_path = ProjectScaffolder.delete(project)
        ManifestGenerator.delete(project)
        return project_path

    @staticmethod
    def list_projects() -> list[Manifest]:
        return list(load_projects().values())

    @staticmethod
    def get_project(project_id: str) -> Manifest:
        project = load_projects().get(project_id)
        if not project:
            raise ProjectNotFoundError(f"Projeto não encontrado: {project_id}")
        return project

    @staticmethod
    def build_project_files(project_id: str, project: Manifest) -> dict[str, str]:
        inputs_folder = INPUTS_DIR / project_id
        return {
            required_file.id: str(
                inputs_folder / f"{required_file.id}.{required_file.accepted_extensions[0]}"
            )
            for required_file in project.required_files
        }

    @staticmethod
    def get_project_output_folder(project: Manifest) -> Path:
        output_folder = getattr(project, "output_folder", "data/output")
        return BASE_DIR / project.project_path / output_folder

    @staticmethod
    def validate_uploaded_files(
        project_id: str,
        project: Manifest,
        uploaded_files: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], bool]:

        validation_results = []
        all_valid = True

        for file_definition in project.required_files:
            file_id = file_definition.id
            uploaded_file = uploaded_files.get(file_id)

            if uploaded_file is None:
                all_valid = False
                continue

            try:
                file_name = getattr(
                    uploaded_file,
                    "name",
                    None,
                ) or getattr(
                    uploaded_file,
                    "filename",
                    None,
                )

                if file_name is None:
                    raise ValueError("Nome do arquivo não encontrado.")

                content = (
                    uploaded_file.getbuffer()
                    if hasattr(uploaded_file, "getbuffer")
                    else uploaded_file.file.read()
                )

                saved_file = FileManager.save_uploaded_file(
                    project_id=project_id,
                    file_id=file_id,
                    file_name=file_name,
                    content=content,
                )

                result = Validator.validate_file(
                    file_path=saved_file,
                    file_definition=file_definition,
                )
                validation_results.append(result)

                if not result["valid"]:
                    all_valid = False

            except FileProcessingError as e:
                logger.error(f"Erro ao processar arquivo {file_id}: {str(e)}")
                validation_results.append({
                    "file_id": file_id,
                    "display_name": file_definition.display_name,
                    "valid": False,
                    "score": 0,
                    "missing_columns": [],
                    "error": str(e),
                })
                all_valid = False

            except Exception as e:
                logger.error(f"Erro inesperado ao processar arquivo {file_id}: {str(e)}")
                validation_results.append({
                    "file_id": file_id,
                    "display_name": file_definition.display_name,
                    "valid": False,
                    "score": 0,
                    "missing_columns": [],
                    "error": f"Erro inesperado: {str(e)}",
                })
                all_valid = False

        return validation_results, all_valid

    @staticmethod
    def validate_outputs(project: Manifest) -> dict[str, Any]:
        return OutputValidator.validate(
            output_folder=Orchestrator.get_project_output_folder(project),
            expected_outputs=project.outputs,
        )

    @classmethod
    def run_project(
        cls,
        project_id: str,
        uploaded_files: list[Any],
        execution_id: Optional[str] = None,
    ) -> RunProjectResult:
        project = cls.get_project(project_id)
        
        mapped_files = UploadMapper.map_uploaded_files(
            project_id=project_id,
            uploaded_files=uploaded_files,
        )

        project_files = cls.build_project_files(
            project_id=project_id,
            project=project,
        )

        execution_id = execution_id or ExecutionLogger.create_execution_id()

        context = ExecutionContext(
            execution_id=execution_id,
            project_id=project_id,
            started_at=datetime.now(),
            manifest=project,
            inputs=project_files,
            storage_provider=get_storage_provider().name,
            working_directory=str(
                (BASE_DIR / project.project_path).resolve()
            ),
        )

        execution_result = Executor.run(
            project_id=project_id,
            files=project_files,
        )

        execution_result.execution_id = execution_id
        execution_result.started_at = context.started_at
        execution_result.finished_at = datetime.now()
        execution_result.user = "Usuário Local"
        execution_result.uploaded_files = [
            getattr(uploaded_file, "name", "arquivo")
            for uploaded_file in uploaded_files
        ]

        output_result = OutputValidator.validate(
            output_folder=cls.get_project_output_folder(project),
            expected_outputs=project.outputs,
        )

        execution_result.outputs = [
            output["name"]
            for output in output_result["found"]
        ]

        ExecutionLogger.save(execution_result)

        if execution_result.status == ExecutionStatus.FAILED:
            raw_error = execution_result.error_message or "Erro desconhecido na execução do ETL."
            if "merge on int64 and str" in raw_error:
                raw_error += "\n\n[DICA MELLO BOT]: Você está tentando cruzar dados com tipos diferentes (int e texto) na chave de merge. Normalize a coluna para string e remada formatação antes do merge usando astype(str)."
            logger.error(f"Execução falhou para projeto {project_id}: {raw_error}")
            raise RuntimeError(raw_error)

        return RunProjectResult(
            status=execution_result.status.value,
            mapped_files=list(mapped_files.keys()),
            outputs=[output["name"] for output in output_result["found"]],
        )

@classmethod
def generate_project_script(cls, project: Manifest) -> str:
    """Gera o script do projeto usando o template adequado"""
    template_engine = TemplateEngine()
    template_name = project.pattern or "generic"
    
    # Renderiza o template com os dados do projeto
    script = template_engine.render(
        f"{template_name}_main.py.j2",
        project=project
    )
    
    return script
###PATH:core\execution_logger.py