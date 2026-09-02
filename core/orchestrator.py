from core.models import Manifest
from core.registry import load_projects


class Orchestrator:

    @staticmethod
    def list_projects() -> list[Manifest]:
        return list(load_projects().values())