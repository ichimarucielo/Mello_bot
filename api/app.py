from pathlib import Path
from fastapi import FastAPI, HTTPException
from core.executor import Executor
from core.registry import load_projects
from fastapi import File
from fastapi import UploadFile
from core.upload_mapper import UploadMapper
from core.output_validator import OutputValidator
from typing import Annotated

app = FastAPI(
    title="MELLO BOT API",
    version="1.0.0",
)


@app.get("/health")
def health():

    return {
        "status": "ok",
    }


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


@app.post("/execute/{project_id}")
def execute_project(
    project_id: str,
):

    projects = load_projects()

    if project_id not in projects:

        raise HTTPException(
            status_code=404,
            detail=f"Projeto '{project_id}' não encontrado.",
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

    try:

        Executor.run(
            project_id=project_id,
            files={
                "prefeitura": str(
                    inputs_folder / "prefeitura.csv"
                ),
                "fs10n": str(
                    inputs_folder / "fs10n.xlsx"
                ),
                "zsd008": str(
                    inputs_folder / "zsd008.xlsx"
                ),
            },
        )

        return {
            "status": "success",
            "project_id": project_id,
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )

@app.post("/projects/{project_id}/run")
async def run_project(
    project_id: str,
    files: list[UploadFile] = File(...),
):

    return {
        "project_id": project_id,
        "files": [
            file.filename
            for file in files
        ]
    }

@app.post("/test-upload")
async def test_upload(
    files: list[UploadFile] = File(...)
):

    return {
        "count": len(files),
        "files": [
            file.filename
            for file in files
        ]
    }