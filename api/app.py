from fastapi import BackgroundTasks, FastAPI, HTTPException
from api.schemas import (
    CreateExecutionRequest,
    CreateExecutionResponse,
    ExecutionFilesResponse,
    ExecuteResponse,
    HealthDetailResponse,
    HealthResponse,
    HistoryResponse,
    AIAnalyzeResponse,
    AIManifestResponse,
    AICreateProjectResponse,
    AICreateProjectRequest,
    OutputResponse,
    ProjectResponse,
    RunResponse,
)
from core.executor import Executor
from core.orchestrator import Orchestrator
from fastapi import File, HTTPException
from fastapi import UploadFile
from typing import Annotated
from fastapi.responses import FileResponse
from core.history_service import HistoryService
from core.health_service import HealthService
from core.exceptions import ProjectNotFoundError
from core.execution_service import ExecutionService, StagedUpload
from core.automation_designer import AutomationDesigner
from core.models import AutomationRequest
from core.manifest_generator import ManifestGenerator

app = FastAPI(
    title="MELLO BOT API",
    version="1.0.0",
)


@app.post(
    "/ai/analyze",
    response_model=AIAnalyzeResponse,
)
def analyze_automation(request: AutomationRequest):
    analysis = AutomationDesigner().analyze(request.prompt)
    return AIAnalyzeResponse.model_validate(analysis.model_dump(mode="json"))


@app.post(
    "/ai/manifest",
    response_model=AIManifestResponse,
)
def generate_automation_manifest(request: AutomationRequest):
    if request.manifest_data:
        manifest = ManifestGenerator.validate(request.manifest_data)
        return {"manifest": ManifestGenerator.to_yaml(manifest)}
    return {"manifest": AutomationDesigner().generate_manifest(request.prompt)}


@app.post(
    "/ai/create-project",
    response_model=AICreateProjectResponse,
    status_code=201,
)
def create_automation_project(request: AICreateProjectRequest):
    if not request.approved:
        raise HTTPException(
            status_code=409,
            detail="A aprovação humana do Execution Plan é obrigatória.",
        )

    designer = AutomationDesigner()
    manifest_data = getattr(request, "manifest_data", None)
    try:
        result = (
            designer.create_project_from_manifest(manifest_data)
            if manifest_data
            else designer.create_project(request.prompt)
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return result.model_dump(
        include={
            "project_id",
            "project_path",
            "manifest_path",
            "readme_path",
            "entrypoint_path",
            "published_manifest_path",
            "status",
        }
    )


@app.post(
    "/executions",
    response_model=CreateExecutionResponse,
    status_code=202,
)
def create_execution(request: CreateExecutionRequest):
    try:
        execution = ExecutionService.create(request.project_id)
    except ProjectNotFoundError:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    return {
        "execution_id": execution["execution_id"],
        "status": execution["status"],
    }


@app.post(
    "/executions/{execution_id}/files",
    response_model=ExecutionFilesResponse,
    status_code=202,
)
async def upload_execution_files(
    execution_id: str,
    background_tasks: BackgroundTasks,
    files: Annotated[
        list[UploadFile],
        File(description="Arquivos de entrada da execução"),
    ] = ...,
):
    if HistoryService.get_execution(execution_id) is None:
        raise HTTPException(status_code=404, detail="Execução não encontrada")

    staged_files = [
        StagedUpload(
            name=file.filename or "arquivo",
            content=await file.read(),
        )
        for file in files
    ]
    try:
        uploaded_files = ExecutionService.stage_files(execution_id, staged_files)
    except KeyError:
        raise HTTPException(status_code=404, detail="Execução não encontrada")

    background_tasks.add_task(ExecutionService.run, execution_id)
    return {
        "execution_id": execution_id,
        "status": "pending",
        "uploaded_files": uploaded_files,
    }


@app.get(
    "/executions",
    response_model=list[HistoryResponse],
)
def list_executions():
    return HistoryService.get_history(limit=100)


@app.get(
    "/executions/{execution_id}",
    response_model=HistoryResponse,
)
def get_execution_details(execution_id: str):
    execution = HistoryService.get_execution(execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="Execução não encontrada")
    return execution


@app.get(
    "/executions/{execution_id}/outputs",
    response_model=list[OutputResponse],
)
def get_execution_outputs(execution_id: str):
    execution = HistoryService.get_execution(execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="Execução não encontrada")

    try:
        project = Orchestrator.get_project(execution["project_id"])
    except ProjectNotFoundError:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    output_folder = Orchestrator.get_project_output_folder(project)
    return [
        {
            "name": output_name,
            "size_bytes": (output_folder / output_name).stat().st_size,
        }
        for output_name in execution.get("outputs", [])
        if (output_folder / output_name).is_file()
    ]


@app.get(
    "/health",
    response_model=HealthResponse,
)
def health():

    return HealthResponse(
        status="ok"
    )


@app.get(
    "/health/details",
    response_model=HealthDetailResponse,
)
def health_details():
    return HealthService.diagnose_details()


@app.get(
    "/projects",
    response_model=list[ProjectResponse],
)
def list_projects():

    projects = []

    for project in Orchestrator.list_projects():

        projects.append(
            {
                "id": project.id,
                "name": project.name,
                "category": project.category,
                "description": project.description,
            }
        )

    return projects

@app.get(
    "/projects/{project_id}",
    response_model=ProjectResponse,
)
def get_project(
    project_id: str,
):

    try:
        project = Orchestrator.get_project(
            project_id
        )
    except ProjectNotFoundError:

        raise HTTPException(
            status_code=404,
            detail="Projeto não encontrado",
        )

    return project

@app.get(
    "/projects/{project_id}/outputs/{file_name}"
)
def download_output(
    project_id: str,
    file_name: str,
):

    try:
        project = Orchestrator.get_project(
            project_id
        )
    except ProjectNotFoundError:

        raise HTTPException(
            status_code=404,
            detail="Projeto não encontrado",
        )

    output_folder = (
        Orchestrator.get_project_output_folder(
            project
        )
    )

    file_path = (
        output_folder /
        file_name
    )

    if not file_path.exists():

        raise HTTPException(
            status_code=404,
            detail="Arquivo não encontrado",
        )

    return FileResponse(
        path=file_path,
        filename=file_name,
    )

@app.get(
    "/projects/{project_id}/outputs",
    response_model=list[OutputResponse],
)
def list_outputs(
    project_id: str,
):

    try:
        project = Orchestrator.get_project(
            project_id
        )
    except ProjectNotFoundError:

        raise HTTPException(
            status_code=404,
            detail="Projeto não encontrado",
        )

    output_folder = (
    Orchestrator.get_project_output_folder(
        project
        )
    )

    outputs = []

    for file_name in project.outputs:

        file_path = (
            output_folder /
            file_name
        )

        if file_path.exists():

            outputs.append(
                {
                    "name": file_name,
                    "size_bytes": file_path.stat().st_size,
                }
            )

    return outputs

@app.get(
    "/history",
    response_model=list[HistoryResponse],
)
def get_history():

    return HistoryService.get_history(
        limit=100
    )

@app.get(
    "/history/{execution_id}",
    response_model=HistoryResponse,
)
def get_execution(
    execution_id: str,
):

    executions = (
        HistoryService.get_history(
            limit=1000
        )
    )

    for execution in executions:

        if (
            execution.get(
                "execution_id"
            )
            == execution_id
        ):

            return execution

    raise HTTPException(
        status_code=404,
        detail="Execução não encontrada",
    )

@app.post(
    "/execute/{project_id}",
    response_model=ExecuteResponse,
)
def execute_project(
    project_id: str,
):

    try:
        project = Orchestrator.get_project(
            project_id
        )
    except ProjectNotFoundError:

        raise HTTPException(
            status_code=404,
            detail=f"Projeto '{project_id}' não encontrado.",
        )

    try:

        project_files = Orchestrator.build_project_files(
            project_id=project_id,
            project=project,
        )

        execution_result = Executor.run(
            project_id=project_id,
            files=project_files,
        )

        if execution_result.status.value != "success":
            raise HTTPException(
                status_code=500,
                detail=execution_result.error_message or "A execução falhou.",
            )

        output_result = Orchestrator.validate_outputs(project)
        if not output_result["valid"]:
            raise HTTPException(
                status_code=500,
                detail=(
                    "A execução terminou sem gerar todos os outputs declarados: "
                    + ", ".join(output_result["missing"])
                ),
            )

        return {
            "status": "success",
            "project_id": project_id,
            "files": project_files,
            "outputs": [item["name"] for item in output_result["found"]],
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )
    
@app.post(
    "/projects/{project_id}/run",
    response_model=RunResponse,
)
async def run_project(
    project_id: str,
    files: Annotated[
        list[UploadFile],
        File(description="Arquivos do projeto a serem processados"),
    ] = ...,
):
    try:
        return Orchestrator.run_project(
            project_id=project_id,
            uploaded_files=files,
        )

    except ProjectNotFoundError:

        raise HTTPException(
            status_code=404,
            detail="Projeto não encontrado",
        )

@app.post("/test-upload")
async def test_upload(
    files: Annotated[
        list[UploadFile],
        File(description="Arquivos de teste"),
    ] = ...,
):

    return {
        "count": len(files),
        "files": [
            file.filename
            for file in files
        ]
    }

