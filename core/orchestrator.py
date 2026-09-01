from core.models import Manifest
from core.registry import load_projects


class Orchestrator:

    @staticmethod
    def list_projects() -> listreturn list(load_projects().values())