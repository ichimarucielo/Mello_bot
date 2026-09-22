from abc import ABC, abstractmethod
import re
import unicodedata
from typing import Any

from core.manifest_generator import ManifestGenerator
from core.models import AutomationAnalysis
from core.document_catalog import DocumentCatalog

class AIService(ABC):
    """Contrato para provedores de analise de automacoes."""

    @abstractmethod
    def analyze(self, prompt: str) -> AutomationAnalysis:
        raise NotImplementedError


class MockAIService(AIService):
    """Analisador local deterministico para desenvolvimento e testes."""

    CATALOG = DocumentCatalog()

    SAP_REPORT_TERMS = (
        "fs10n",
        "fbl3n",
        "fbl5n",
        "fbl5n aberta",
        "fbl5n compensada",
        "zsd008",
        "zfaturamento",
    )

    DOMAIN_EXTENSIONS = {
        "sap": "xlsx",
        "billing": "xlsx",
        "prefeitura": "csv",
        "antifraude": "xlsx",
    }

    SOURCE_PATTERNS = {
        "contas_pagar": (
            "contas a pagar",
            "contas pagar",
            "contas_pagar",
            "a pagar",
        ),
        "contas_receber": (
            "contas a receber",
            "contas receber",
            "contas_receber",
            "a receber",
        ),
        "sap": ("sap",) + SAP_REPORT_TERMS,
        "billing": ("billing", "billings"),
        "antifraude": ("antifraude", "fraude", "risco"),
        "salesforce": ("salesforce", "sales force"),
        "prefeitura": ("prefeitura", "rps", "nota fiscal"),
    }

    FINANCIAL_TERMS = (
        "contas",
        "faturamento",
        "billing",
        "financeiro",
        "fornecedor",
        "pagamento",
        "recebimento",
        "sap",
    )

    RECONCILIATION_TERMS = (
        "compar",
        "concili",
        "diverg",
        "cruz",
        "confront",
        "apenas sap",
        "apenas billing",
    )

    CONSOLIDATION_TERMS = (
        "consolidar",
        "agrup",
        "unificar",
        "consolidado",
    )

    POWER_BI_TERMS = ("power bi", "dashboard", "dataset")

    ANTIFRAUD_TERMS = ("antifraude", "fraude", "risco")

    VALIDATION_TERMS = ("validar", "validacao", "validacao de dados")

    def analyze(self, prompt: str) -> AutomationAnalysis:
        normalized_prompt = prompt.strip()
        prompt_lower = self._normalize(normalized_prompt)
        file_entities = self._detect_file_entities(prompt_lower)
        sources = self._detect_sources(prompt_lower, file_entities)
        reconciliation = self._is_reconciliation(
            prompt_lower,
            sources,
            file_entities,
        )
        consolidation = self._is_consolidation(prompt_lower)
        power_bi = self._is_power_bi(prompt_lower)
        pattern = self._pattern(
            prompt_lower,
            reconciliation,
            consolidation,
            power_bi,
        )
        project_id = self._project_id(
            prompt_lower,
            sources,
            reconciliation,
            consolidation,
            power_bi,
        )
        project_name = self._project_name(
            sources,
            reconciliation,
            consolidation,
            power_bi,
        )
        category = self._category(sources, reconciliation, power_bi, prompt_lower)
        inputs = self._inputs(
            prompt_lower,
            sources,
            reconciliation,
            power_bi,
            file_entities,
        )
        outputs = self._outputs(
            sources,
            reconciliation,
            consolidation,
            power_bi,
        )
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
            pattern=pattern,
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
    def _detect_sources(
        cls,
        prompt: str,
        file_entities: list[dict[str, Any]],
    ) -> list[str]:
        detected = [
            source
            for source, patterns in cls.SOURCE_PATTERNS.items()
            if any(pattern in prompt for pattern in patterns)
        ]
        for entity in file_entities:
            source = entity["source"]
            if source not in detected:
                detected.append(source)
        return detected

    @classmethod
    def _detect_file_entities(cls, prompt: str) -> list[dict[str, Any]]:
        entities: list[dict[str, Any]] = []

        for report in ("zsd008", "fs10n", "fbl3n"):
            matches = list(re.finditer(rf"\b{report}\b", prompt))
            for index, match in enumerate(matches):
                next_start = matches[index + 1].start() if index + 1 < len(matches) else len(prompt)
                context = prompt[match.end():min(next_start, match.end() + 36)]
                qualifier = cls._clean_qualifier(context)
                file_id = f"{report}_{qualifier}" if qualifier else "sap"
                suffix = f"_{qualifier}" if qualifier else ""
                entities.append(
                    cls._file_entity(
                        file_id=file_id,
                        display_name=(
                            f"{report.upper()} {qualifier.replace('_', ' ').title()}"
                            if qualifier
                            else "SAP"
                        ),
                        source="sap",
                        report=report,
                        extension="xlsx",
                        attributes={"qualifier": qualifier},
                    )
                )

        for match in re.finditer(r"\bfbl5n\b", prompt):
            context = prompt[match.end():match.end() + 24]
            qualifier = cls._clean_qualifier(context)
            file_id = f"fbl5n_{qualifier}" if qualifier else "sap"
            entities.append(
                cls._file_entity(
                    file_id=file_id,
                    display_name=f"FBL5N {qualifier.replace('_', ' ').title()}".strip(),
                    source="sap",
                    report="fbl5n",
                    extension="xlsx",
                    attributes={"qualifier": qualifier},
                )
            )

        if "contas a pagar" in prompt and "contas a receber" in prompt:
            entities.extend(
                [
                    cls._file_entity(
                        "contas_pagar", "Contas a Pagar", "contas_pagar", "xlsx",
                        attributes={"context": "contas a pagar"},
                    ),
                    cls._file_entity(
                        "contas_receber", "Contas a Receber", "contas_receber", "xlsx",
                        attributes={"context": "contas a receber"},
                    ),
                ]
            )

        if "billing" in prompt:
            entities.append(
                cls._file_entity(
                    "billing", "Billing", "billing", "xlsx",
                    attributes={"context": "billing"},
                )
            )
        if "prefeitura" in prompt:
            entities.append(
                cls._file_entity(
                    "prefeitura", "Prefeitura", "prefeitura", "csv",
                    attributes={"context": "prefeitura"},
                )
            )
        if not entities and any(term in prompt for term in cls.ANTIFRAUD_TERMS):
            entities.append(
                cls._file_entity(
                    "base_antifraude", "Base Antifraude", "antifraude", "xlsx",
                    attributes={"context": "antifraude"},
                )
            )
        return cls._deduplicate_entities(entities)
    
    @staticmethod
    def _file_entity(
        file_id: str,
        display_name: str,
        source: str,
        extension: str,
        report: str | None = None,
        attributes: dict[str, str] | None = None,
    ) -> dict[str, Any]:

        document = MockAIService.CATALOG.documents.get(
            report or source
        )

        return {
            "id": file_id,
            "display_name": display_name,
            "source": source,
            "report": report or source,
            "extension": extension,
            "cli_argument": f"--{file_id.replace('_', '-')}",
            "required_columns": (
                document.get("required_columns", [])
                if document
                else []
            ),
            "attributes": attributes or {},
        }

    @staticmethod
    def _clean_qualifier(value: str) -> str:
        value = re.sub(r"\b(?:e|outro|do|de|mes)\b", " ", value)

        month_match = re.search(
            r"\b(?:mes\s*)?(\d{1,2})\b",
            value,
        )

        if month_match:
            return f"mes_{month_match.group(1)}"

        tokens = re.findall(
            r"[a-z0-9]+",
            value,
        )

        for token in (
            "atual",
            "anterior",
            "historico",
            "aberta",
            "compensada",
            "fechada",
            "pendente",
        ):
            if token in tokens:
                return token

        return ""

    @staticmethod
    def _deduplicate_entities(
        entities: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:

        unique: list[dict[str, Any]] = []
        seen: set[str] = set()

        for entity in entities:
            if entity["id"] not in seen:
                unique.append(entity)
                seen.add(entity["id"])

        return unique

    @classmethod
    def _is_consolidation(cls, prompt: str) -> bool:
        return any(term in prompt for term in cls.CONSOLIDATION_TERMS)

    @classmethod
    def _is_power_bi(cls, prompt: str) -> bool:
        return any(term in prompt for term in cls.POWER_BI_TERMS)

    @classmethod
    def _pattern(
        cls,
        prompt: str,
        reconciliation: bool,
        consolidation: bool,
        power_bi: bool,
    ) -> str:
        if reconciliation:
            return "reconciliation"
        if consolidation:
            return "consolidation"
        if any(term in prompt for term in cls.ANTIFRAUD_TERMS):
            return "antifraud"
        if power_bi:
            return "powerbi"
        if any(term in prompt for term in cls.VALIDATION_TERMS):
            return "validation"
        return "generic"

    @classmethod
    def _is_reconciliation(
        cls,
        prompt: str,
        sources: list[str],
        file_entities: list[dict[str, Any]],
    ) -> bool:
        return (
            len(file_entities) >= 2
            and any(term in prompt for term in cls.RECONCILIATION_TERMS)
        ) or {"sap", "billing"}.issubset(sources) or len(file_entities) >= 2

    @staticmethod
    def _project_id(
        prompt: str,
        sources: list[str],
        reconciliation: bool,
        consolidation: bool,
        power_bi: bool,
    ) -> str:
        if power_bi and not reconciliation:
            base = "dataset_power_bi"
        elif any(term in prompt for term in MockAIService.ANTIFRAUD_TERMS):
            base = "antifraude"
        elif reconciliation and {"contas_pagar", "contas_receber"}.issubset(sources):
            base = "conciliacao_contas_pagar_receber"
        elif reconciliation and {"sap", "billing"}.issubset(sources):
            base = "conciliacao_sap_billing"
        elif reconciliation:
            base = "conciliacao_" + "_".join(sources[:2] or ["arquivos"])
        elif consolidation:
            base = "consolidacao_" + (sources[0] if sources else "dados")
        elif sources:
            base = sources[0]
        else:
            base = "automacao"
        return re.sub(r"[^a-z0-9]+", "_", base).strip("_")

    @staticmethod
    def _project_name(
        sources: list[str],
        reconciliation: bool,
        consolidation: bool,
        power_bi: bool,
    ) -> str:
        if power_bi and not reconciliation:
            return "Dataset Power BI"
        if any(term in " ".join(sources) for term in ("antifraude", "fraude", "risco")):
            return "Antifraude"
        if reconciliation and {"contas_pagar", "contas_receber"}.issubset(sources):
            return "Conciliacao Contas a Pagar x Contas a Receber"
        if reconciliation and {"sap", "billing"}.issubset(sources):
            return "Conciliacao SAP x Billing"
        if reconciliation:
            return "Conciliacao " + " x ".join(source.upper() for source in sources)
        if consolidation:
            return "Consolidacao " + (sources[0].replace("_", " ").title() if sources else "Dados")
        return "Automacao " + (sources[0].capitalize() if sources else "Gerada")

    @staticmethod
    def _category(
        sources: list[str],
        reconciliation: bool,
        power_bi: bool,
        prompt: str,
    ) -> str:
        if power_bi and not reconciliation:
            return "power_bi"
        if any(term in prompt for term in MockAIService.ANTIFRAUD_TERMS):
            return "risco"
        if reconciliation or any(source in {"sap", "billing", "contas_pagar", "contas_receber"} for source in sources):
            return "financeiro"
        if any(term in prompt for term in MockAIService.FINANCIAL_TERMS):
            return "financeiro"
        if "salesforce" in sources:
            return "salesforce"
        return "operacional"

    @staticmethod
    def _outputs(
        sources: list[str],
        reconciliation: bool,
        consolidation: bool,
        power_bi: bool,
    ) -> list[str]:
        if power_bi and not reconciliation:
            return ["dataset.csv"]
        if any(term in sources for term in ("antifraude", "fraude", "risco")):
            return ["antifraude.xlsx"]
        if consolidation and not reconciliation:
            return ["consolidado.xlsx"]
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
        power_bi: bool,
        file_entities: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if file_entities:
            return file_entities
        extension = MockAIService._preferred_extension(prompt, sources)
        if power_bi and not reconciliation:
            return [
                {
                    "id": "origem",
                    "display_name": "Base de origem",
                    "cli_argument": "--input-file",
                    "extension": extension,
                    "required_columns": ["ID"],
                }
            ]
        if any(term in prompt for term in MockAIService.ANTIFRAUD_TERMS):
            return [
                {
                    "id": "base_antifraude",
                    "display_name": "Base Antifraude",
                    "cli_argument": "--input-file",
                    "extension": extension,
                    "required_columns": ["ID"],
                }
            ]
        if reconciliation and {"contas_pagar", "contas_receber"}.issubset(sources):
            return [
                {
                    "id": "contas_pagar",
                    "display_name": "Contas a Pagar",
                    "cli_argument": "--contas-pagar",
                    "extension": extension,
                    "required_columns": ["DOCUMENTO"],
                },
                {
                    "id": "contas_receber",
                    "display_name": "Contas a Receber",
                    "cli_argument": "--contas-receber",
                    "extension": extension,
                    "required_columns": ["DOCUMENTO"],
                },
            ]
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

    @classmethod
    def _preferred_extension(cls, prompt: str, sources: list[str]) -> str:
        if any(term in prompt for term in cls.SAP_REPORT_TERMS):
            return cls.DOMAIN_EXTENSIONS["sap"]
        for source in sources:
            if source in cls.DOMAIN_EXTENSIONS:
                return cls.DOMAIN_EXTENSIONS[source]
        if any(term in prompt for term in ("excel", "xlsx", "relatorio")):
            return "xlsx"
        return "csv"