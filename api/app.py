from fastapi import FastAPI, HTTPException
from api.schemas import (
    ExecuteResponse,
    HealthResponse,
    HistoryResponse,
    OutputResponse,
    ProjectResponse,
    RunResponse,
)
from core.executor import Executor
from core.orchestrator import Orchestrator
from fastapi import File
from fastapi import UploadFile
from typing import Annotated
from fastapi.responses import FileResponse
from core.history_service import HistoryService
from core.exceptions import ProjectNotFoundError

app = FastAPI(
    title="MELLO BOT API",
    version="1.0.0",
)


@app.get(
    "/health",
    response_model=HealthResponse,
)
def health():

    return HealthResponse(
        status="ok"
    )


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

        Executor.run(
            project_id=project_id,
            files=project_files,
        )

        return {
            "status": "success",
            "project_id": project_id,
            "files": project_files,
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

