from pydantic import BaseModel


class HealthResponse(
    BaseModel
):
    status: str


class OutputResponse(
    BaseModel
):
    name: str
    size_bytes: int


class RunResponse(
    BaseModel
):
    status: str
    mapped_files: list[str]
    outputs: list[str]