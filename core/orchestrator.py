from core.registry import load_projects


class Orchestrator:

    @staticmethod
    def list_projects():

        return list(load_projects().values())