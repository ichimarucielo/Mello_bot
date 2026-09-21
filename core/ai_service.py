from abc import ABC, abstractmethod
import re
import unicodedata
from typing import Any

from core.manifest_generator import ManifestGenerator
from core.models import AutomationAnalysis


class AIService(ABC):
    """Contrato para provedores de analise de automacoes."""

    @abstractmethod
    def analyze(self, prompt: str) -> AutomationAnalysis:
        raise NotImplementedError


class MockAIService(AIService):
    """Analisador local deterministico para desenvolvimento e testes."""

    SOURCE_PATTERNS = {
        "sap": ("sap", "fs10n", "fbl3n", "zsd008", "zfaturamento"),
        "billing": ("billing", "billings"),
        "salesforce": ("salesforce", "sales force"),
        "prefeitura": ("prefeitura", "rps", "nota fiscal"),
    }

    RECONCILIATION_TERMS = (
        "compar",
        "concili",
        "diverg",
        "cruz",
        "confront",
        "apenas sap",
        "apenas billing",
    )

    def analyze(self, prompt: str) -> AutomationAnalysis:
        normalized_prompt = prompt.strip()
        prompt_lower = self._normalize(normalized_prompt)
        sources = self._detect_sources(prompt_lower)
        reconciliation = self._is_reconciliation(prompt_lower, sources)
        project_id = self._project_id(prompt_lower, sources, reconciliation)
        project_name = self._project_name(sources, reconciliation)
        category = self._category(sources, reconciliation)
        inputs = self._inputs(prompt_lower, sources, reconciliation)
        outputs = self._outputs(sources, reconciliation)
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
                f"Padrao identificado: {'conciliacao' if reconciliation else 'processamento'}. "
                f"Fontes detectadas: {', '.join(sources) or 'nao identificadas'}. "
                "Os nomes das colunas ainda devem ser confirmados com os arquivos reais."
            ),
            viability=(
                "Viavel como scaffold inicial; confirme os argumentos CLI, "
                "colunas obrigatorias e regras de conciliacao antes da execucao."
            ),
            inputs=inputs,
            outputs=outputs,
            complexity="media" if reconciliation or len(inputs) > 1 else "baixa",
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
    def _normalize(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value.lower())
        return "".join(
            character
            for character in normalized
            if not unicodedata.combining(character)
        )

    @classmethod
    def _detect_sources(cls, prompt: str) -> list[str]:
        return [
            source
            for source, patterns in cls.SOURCE_PATTERNS.items()
            if any(pattern in prompt for pattern in patterns)
        ]

    @classmethod
    def _is_reconciliation(cls, prompt: str, sources: list[str]) -> bool:
        return len(sources) >= 2 and any(
            term in prompt for term in cls.RECONCILIATION_TERMS
        ) or {"sap", "billing"}.issubset(sources)

    @staticmethod
    def _project_id(
        prompt: str,
        sources: list[str],
        reconciliation: bool,
    ) -> str:
        if reconciliation and {"sap", "billing"}.issubset(sources):
            base = "conciliacao_sap_billing"
        elif reconciliation:
            base = "conciliacao_" + "_".join(sources[:2])
        elif sources:
            base = sources[0]
        else:
            base = "automacao"
        return re.sub(r"[^a-z0-9]+", "_", base).strip("_")

    @staticmethod
    def _project_name(sources: list[str], reconciliation: bool) -> str:
        if reconciliation and {"sap", "billing"}.issubset(sources):
            return "Conciliacao SAP x Billing"
        if reconciliation:
            return "Conciliacao " + " x ".join(source.upper() for source in sources)
        return "Automacao " + (sources[0].capitalize() if sources else "Gerada")

    @staticmethod
    def _category(sources: list[str], reconciliation: bool) -> str:
        if reconciliation or {"sap", "billing"}.intersection(sources):
            return "financeiro"
        if "salesforce" in sources:
            return "salesforce"
        return "operacional"

    @staticmethod
    def _outputs(sources: list[str], reconciliation: bool) -> list[str]:
        if reconciliation and {"sap", "billing"}.issubset(sources):
            return ["conciliacao.xlsx", "divergencias.xlsx"]
        if reconciliation:
            return ["conciliacao.xlsx", "divergencias.xlsx"]
        return ["resultado.xlsx"]

    @staticmethod
    def _inputs(
        prompt: str,
        sources: list[str],
        reconciliation: bool,
    ) -> list[dict[str, Any]]:
        extension = "xlsx" if any(
            term in prompt for term in ("excel", "xlsx", "relatorio", "fs10n")
        ) else "csv"
        if reconciliation and {"sap", "billing"}.issubset(sources):
            return [
                {
                    "id": "sap",
                    "display_name": "SAP (FS10N)" if "fs10n" in prompt else "SAP",
                    "cli_argument": "--sap",
                    "extension": extension,
                    "required_columns": ["DOCUMENTO"],
                },
                {
                    "id": "billing",
                    "display_name": "Billing",
                    "cli_argument": "--billing",
                    "extension": extension,
                    "required_columns": ["DOCUMENTO"],
                },
            ]
        if sources:
            source = sources[0]
            return [
                {
                    "id": source,
                    "display_name": source.upper(),
                    "cli_argument": "--input-file",
                    "extension": extension,
                    "required_columns": ["ID"],
                }
            ]
        return [
            {
                "id": "entrada",
                "display_name": "Arquivo de entrada",
                "cli_argument": "--input-file",
                "extension": extension,
                "required_columns": ["ID"],
            }
        ]