from fastapi import FastAPI

from core.orchestrator import Orchestrator

app = FastAPI(
    title="MELLO BOT API",
    version="1.0.0",
)


@app.get("/health")
def health():

    return {
        "status": "ok"
    }


@app.get("/projects")
def list_projects():

    return Orchestrator.list_projects()