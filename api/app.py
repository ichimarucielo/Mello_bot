from pathlib import Path
from fastapi import FastAPI, HTTPException
from api.schemas import HealthResponse, RunResponse
from core.executor import Executor
from core.registry import load_projects
from fastapi import File
from fastapi import UploadFile
from core.upload_mapper import UploadMapper
from core.output_validator import OutputValidator
from typing import Annotated
from fastapi.responses import FileResponse
from core.history_service import HistoryService

app = FastAPI(
    title="MELLO BOT API",
    version="1.0.0",
)


def get_project_output_folder(
    project: dict,
) -> Path:

    output_folder = project.get(
        "output_folder",
        "data/output",
    )

    return (
        Path(
            project["project_path"]
        )
        / output_folder
    )

def build_project_files(
    project_id: str,
    project: dict,
) -> dict[str, str]:

    root = (
        Path(__file__)
        .resolve()
        .parent
        .parent
    )

    inputs_folder = (
        root /
        "inputs" /
        project_id
    )

    files = {}

    for required_file in project.get(
        "required_files",
        [],
    ):

        file_id = required_file["id"]

        extension = (
            required_file[
                "accepted_extensions"
            ][0]
        )

        files[file_id] = str(
            inputs_folder /
            f"{file_id}.{extension}"
        )

    return files

@app.get(
    "/health",
    response_model=HealthResponse,
)
def health():

    return HealthResponse(
        status="ok"
    )


@app.get("/projects")
def list_projects():

    projects = []

    for project in load_projects().values():

        projects.append(
            {
                "id": project["id"],
                "name": project["name"],
                "category": project.get(
                    "category"
                ),
                "description": project.get(
                    "description"
                ),
            }
        )

    return projects

@app.get("/projects/{project_id}")
def get_project(
    project_id: str,
):

    projects = load_projects()

    project = projects.get(
        project_id
    )

    if not project:

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

    projects = load_projects()

    project = projects.get(
        project_id
    )

    if not project:

        raise HTTPException(
            status_code=404,
            detail="Projeto não encontrado",
        )

    output_folder = (
        get_project_output_folder(
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
    "/projects/{project_id}/outputs"
)
def list_outputs(
    project_id: str,
):

    projects = load_projects()

    project = projects.get(
        project_id
    )

    if not project:

        raise HTTPException(
            status_code=404,
            detail="Projeto não encontrado",
        )

    output_folder = (
    get_project_output_folder(
        project
        )
    )

    print(output_folder)

    outputs = []

    for file_name in project.get(
        "outputs",
        [],
    ):

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

@app.get("/history")
def get_history():

    return HistoryService.get_history(
        limit=100
    )

@app.get(
    "/history/{execution_id}"
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

@app.post("/execute/{project_id}")
def execute_project(
    project_id: str,
):

    projects = load_projects()

    project = projects.get(
        project_id
    )

    if not project:

        raise HTTPException(
            status_code=404,
            detail=f"Projeto '{project_id}' não encontrado.",
        )

    try:

        project_files = build_project_files(
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

    projects = load_projects()

    project = projects.get(
        project_id
    )

    if not project:

        raise HTTPException(
            status_code=404,
            detail="Projeto não encontrado",
        )

    mapped_files = UploadMapper.map_uploaded_files(
        project_id=project_id,
        uploaded_files=files,
    )

    root = (
        Path(__file__)
        .resolve()
        .parent
        .parent
    )

    inputs_folder = (
        root /
        "inputs" /
        project_id
    )

    project_files = build_project_files(
        project_id=project_id,
        project=project,
    )

    Executor.run(
        project_id=project_id,
        files=project_files,
    )

    project_output_folder = (
        get_project_output_folder(
            project
        )
    )

    output_result = (
        OutputValidator.validate(
            output_folder=project_output_folder,
            expected_outputs=project.get(
                "outputs",
                [],
            ),
        )
    )

    return {
        "status": "success",
        "mapped_files": list(
            mapped_files.keys()
        ),
        "outputs": [
            output["name"]
            for output in output_result[
                "found"
            ]
        ],
    }

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

