from abc import ABC, abstractmethod
import re

from core.manifest_generator import ManifestGenerator
from core.models import AutomationAnalysis


class AIService(ABC):
    """Contrato para provedores de analise de automacoes."""

    @abstractmethod
    def analyze(self, prompt: str) -> AutomationAnalysis:
        raise NotImplementedError


class MockAIService(AIService):
    """Analisador local deterministico para desenvolvimento e testes."""

    def analyze(self, prompt: str) -> AutomationAnalysis:
        normalized_prompt = prompt.strip()
        prompt_lower = normalized_prompt.lower()
        project_id = self._project_id(prompt_lower)
        project_name = self._project_name(prompt_lower)
        category = "faturamento" if "faturamento" in prompt_lower else "operacional"
        inputs = self._inputs(prompt_lower)
        outputs = ["divergencias.xlsx"] if "compar" in prompt_lower else ["resultado.xlsx"]
        description = normalized_prompt.rstrip(".") + "."

        manifest_data = ManifestGenerator.build_manifest_data(
            project_id=project_id,
            name=project_name,
            category=category,
            description=description,
            project_path=f"projects/{project_id}",
            entrypoint="src/main.py",
            file_id=inputs[0]["id"],
            display_name=inputs[0]["display_name"],
            extension=inputs[0]["extension"],
            required_columns=inputs[0]["required_columns"],
            outputs=outputs,
        )
        manifest_data["required_files"] = [
            {
                "id": item["id"],
                "display_name": item["display_name"],
                "cli_argument": item["cli_argument"],
                "accepted_extensions": [item["extension"]],
                "required_columns": item["required_columns"],
            }
            for item in inputs
        ]

        return AutomationAnalysis(
            diagnostic=(
                "Requisito estruturado como automacao orientada por manifesto, "
                "com inputs identificaveis e outputs verificaveis."
            ),
            viability=(
                "Viavel como scaffold inicial; confirme os argumentos, colunas "
                "e regras de negocio do ETL antes da execucao."
            ),
            inputs=inputs,
            outputs=outputs,
            complexity="media" if len(inputs) > 1 else "baixa",
            project_id=project_id,
            project_name=project_name,
            category=category,
            description=description,
            project_path=manifest_data["project_path"],
            entrypoint=manifest_data["entrypoint"]["script"],
            timeout_seconds=manifest_data["timeout_seconds"],
            manifest_data=manifest_data,
        )

    @staticmethod
    def _project_id(prompt: str) -> str:
        base = "faturamento_sap" if "faturamento" in prompt and "sap" in prompt else "automacao"
        return re.sub(r"[^a-z0-9]+", "_", base).strip("_")

    @staticmethod
    def _project_name(prompt: str) -> str:
        if "faturamento" in prompt and "sap" in prompt:
            return "Conciliacao Faturamento SAP"
        return "Automacao Gerada"

    @staticmethod
    def _inputs(prompt: str) -> list[dict[str, str]]:
        inputs = [
            {
                "id": "entrada",
                "display_name": "Arquivo de entrada",
                "cli_argument": "--input-file",
                "extension": "xlsx" if "excel" in prompt or "xlsx" in prompt else "csv",
                "required_columns": ["ID"],
            }
        ]
        if "sap" in prompt:
            inputs[0]["id"] = "faturamento"
            inputs[0]["display_name"] = "Faturamento"
            inputs[0]["cli_argument"] = "--faturamento"
            inputs.append(
                {
                    "id": "sap",
                    "display_name": "SAP",
                    "cli_argument": "--sap",
                    "extension": "xlsx",
                    "required_columns": ["ID"],
                }
            )
        return inputs