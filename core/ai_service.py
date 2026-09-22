from abc import ABC, abstractmethod
import re
import unicodedata
from typing import Any

from core.manifest_generator import ManifestGenerator
from core.models import AutomationAnalysis
from core.document_catalog import DocumentCatalog
from core.document_engine import FileEntity
from core.pipeline_catalog import mentions

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
        document_ids = self._document_ids(file_entities)
        reconciliation = self._is_reconciliation(
            prompt_lower,
            document_ids,
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
            document_ids,
            reconciliation,
            consolidation,
            power_bi,
        )
        project_name = self._project_name(
            prompt_lower,
            document_ids,
            reconciliation,
            consolidation,
            power_bi,
        )
        category = self._category(document_ids, reconciliation, power_bi, prompt_lower)
        inputs = self._inputs(
            prompt_lower,
            reconciliation,
            power_bi,
            file_entities,
        )
        steps = self._steps(prompt_lower, reconciliation)
        outputs = self._outputs(
            document_ids,
            reconciliation,
            consolidation,
            power_bi,
            prompt_lower,
            steps,
        )
        description = normalized_prompt.rstrip(".") + "."
        understanding = self._understanding(inputs, steps, outputs, project_name)

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
            steps=steps,
        )
        manifest_data["required_files"] = [
            {
                "id": item["id"],
                "display_name": item["display_name"],
                "cli_argument": item["cli_argument"],
                "accepted_extensions": [item["extension"]],
                "critical_columns": item.get("critical_columns", []),
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
            steps=steps,
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
            understanding=understanding,
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
    def _detect_catalog_documents(
        cls,
        prompt: str,
    ) -> list[dict[str, Any]]:

        return [
            cls._file_entity(
                file_id=document.id,
                display_name=document.name,
                source=document.source or document.id,
                report=document.id,
                extension=document.accepted_extensions[0],
            )
            for document in cls.CATALOG.match(prompt)
            if document.accepted_extensions
        ]

    @classmethod
    def _detect_file_entities(cls, prompt: str) -> list[dict[str, Any]]:
        entities = cls._detect_catalog_documents(
            prompt
        )

        for report in ("zsd008", "fs10n", "fbl3n"):
            matches = list(re.finditer(rf"\b{report}\b", prompt))
            for index, match in enumerate(matches):
                next_start = matches[index + 1].start() if index + 1 < len(matches) else len(prompt)
                context = prompt[match.end():min(next_start, match.end() + 36)]
                qualifier = cls._clean_qualifier(context)
                file_id = f"{report}_{qualifier}" if qualifier else report
                suffix = f"_{qualifier}" if qualifier else ""
                document = cls.CATALOG.documents.get(report)
                entities.append(
                    cls._file_entity(
                        file_id=file_id,
                        display_name=(f"{report.upper()} {qualifier.replace('_', ' ').title()}"
                                      if qualifier
                                      else document.get("name", report.upper())
                                      if document
                                      else report.upper()),
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
        qualified_reports = {
            entity["report"]
            for entity in entities
            if entity["id"] != entity["report"]
        }
        entities = [
            entity
            for entity in entities
            if entity["report"] not in qualified_reports
            or entity["id"] != entity["report"]
        ]
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

        entity = FileEntity(
            id=file_id,
            display_name=display_name,
            document_id=report or source,
            extension=extension,
            cli_argument=f"--{file_id.replace('_', '-')}" ,
            required_columns=(document.get("required_columns", []) if document else []),
            critical_columns=(document.get("critical_columns", []) if document else []),
            attributes=attributes or {},
            source=source,
        )
        return entity.as_dict()

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
        document_ids: list[str],
        file_entities: list[dict[str, Any]],
    ) -> bool:
        explicit_reconciliation = any(
            term in prompt
            for term in cls.RECONCILIATION_TERMS
            if term != "cruz"
        )
        known_reconciliation_documents = any(
            document_id in {
                "fbl5n_aberta",
                "fbl5n_compensada",
                "fs10n",
                "billing",
            }
            for document_id in document_ids
        )
        return len(file_entities) >= 2 and (
            explicit_reconciliation or known_reconciliation_documents
        )

    @staticmethod
    def _document_ids(file_entities: list[dict[str, Any]]) -> list[str]:
        return [entity["id"] for entity in file_entities]

    @staticmethod
    def _document_families(document_ids: list[str]) -> list[str]:
        families: list[str] = []
        for document_id in document_ids:
            family = document_id.split("_", 1)[0]
            if family not in families:
                families.append(family)
        return families

    @staticmethod
    def _project_id(
        prompt: str,
        document_ids: list[str],
        reconciliation: bool,
        consolidation: bool,
        power_bi: bool,
    ) -> str:
        if "margem" in prompt and "cliente" in prompt:
            base = "resumo_clientes_vendas"
        elif power_bi and not reconciliation:
            base = "dataset_power_bi"
        elif any(term in prompt for term in MockAIService.ANTIFRAUD_TERMS):
            base = "antifraude"
        elif reconciliation and {"contas_pagar", "contas_receber"}.issubset(document_ids):
            base = "conciliacao_contas_pagar_receber"
        elif reconciliation:
            base = "conciliacao_" + "_".join(
                MockAIService._document_families(document_ids) or ["arquivos"]
            )
        elif consolidation:
            base = "consolidacao_" + (document_ids[0] if document_ids else "dados")
        elif document_ids:
            base = document_ids[0]
        else:
            base = "automacao"
        return re.sub(r"[^a-z0-9]+", "_", base).strip("_")

    @staticmethod
    def _project_name(
        prompt: str,
        document_ids: list[str],
        reconciliation: bool,
        consolidation: bool,
        power_bi: bool,
    ) -> str:
        if "margem" in prompt and "cliente" in prompt:
            return "Análise de Margem por Cliente"
        if power_bi and not reconciliation:
            return "Dataset Power BI"
        if any(term in " ".join(document_ids) for term in ("antifraude", "fraude", "risco")):
            return "Antifraude"
        if reconciliation and {"contas_pagar", "contas_receber"}.issubset(document_ids):
            return "Conciliacao Contas a Pagar x Contas a Receber"
        if reconciliation:
            families = MockAIService._document_families(document_ids)
            return "Conciliacao " + " x ".join(
                family.replace("_", " ").upper() for family in families
            )
        if consolidation:
            return "Consolidacao " + (document_ids[0].replace("_", " ").title() if document_ids else "Dados")
        return "Automacao " + (document_ids[0].replace("_", " ").title() if document_ids else "Gerada")

    @staticmethod
    def _understanding(
        inputs: list[dict[str, Any]],
        steps: list[dict[str, Any]],
        outputs: list[str],
        project_name: str,
    ) -> dict[str, Any]:
        return {
            "document_count": len(inputs),
            "documents": [
                {
                    "id": item["id"],
                    "display_name": item["display_name"],
                }
                for item in inputs
            ],
            "operations": [step["type"] for step in steps],
            "operation_count": len(steps),
            "outputs": outputs,
            "output_count": len(outputs),
            "project_name": project_name,
        }

    @staticmethod
    def _category(
        document_ids: list[str],
        reconciliation: bool,
        power_bi: bool,
        prompt: str,
    ) -> str:
        if power_bi and not reconciliation:
            return "power_bi"
        if any(term in prompt for term in MockAIService.ANTIFRAUD_TERMS):
            return "risco"
        if reconciliation or any(document_id in {"contas_pagar", "contas_receber", "fs10n", "fbl5n_aberta", "fbl5n_compensada", "billing"} for document_id in document_ids):
            return "financeiro"
        if any(term in prompt for term in MockAIService.FINANCIAL_TERMS):
            return "financeiro"
        if "salesforce" in document_ids:
            return "salesforce"
        return "operacional"

    @staticmethod
    def _outputs(
        document_ids: list[str],
        reconciliation: bool,
        consolidation: bool,
        power_bi: bool,
        prompt: str = "",
        steps: list[dict[str, Any]] | None = None,
    ) -> list[str]:
        steps = steps or []
        if power_bi and not reconciliation:
            return ["dataset.csv"]
        if any(term in document_ids for term in ("antifraude", "fraude", "risco")):
            return ["antifraude.xlsx"]
        if not reconciliation and {"calculate", "aggregate"}.issubset(
            step["type"] for step in steps
        ):
            if "resumo" in prompt:
                return ["resumo_clientes.xlsx"]
            if "margem" in prompt and "cliente" in prompt:
                return ["vendas_margem_por_cliente.xlsx"]
            return ["resumo_clientes.xlsx"]
        if consolidation and not reconciliation:
            return ["consolidado.xlsx"]
        if reconciliation:
            if "resumo" in prompt and "julho" in prompt:
                return ["conciliacao_julho.xlsx", "resumo_empresas.xlsx"]
            if "resumo" in prompt:
                return ["conciliacao.xlsx", "resumo_empresas.xlsx"]
            return ["conciliacao.xlsx", "divergencias.xlsx"]
        return ["resultado.xlsx"]

    @staticmethod
    def _steps(prompt: str, reconciliation: bool) -> list[dict[str, Any]]:
        steps: list[dict[str, Any]] = []
        if reconciliation or mentions(prompt, "normalize"):
            steps.append({"type": "normalize"})
        if mentions(prompt, "deduplicate"):
            steps.append({"type": "deduplicate"})
        if mentions(prompt, "remove_nulls"):
            null_column = None
            null_match = re.search(
                r"(?:sem|sem registros? sem|sem registros de|remover registros sem)\s+([a-zà-ú][\wà-ú]*)",
                prompt,
            )
            if null_match:
                null_column = null_match.group(1)
            step = {"type": "remove_nulls"}
            if null_column:
                step["column"] = null_column
            steps.append(step)
        month_match = re.search(
            r"\b(janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\b",
            prompt,
        )
        if month_match:
            months = {
                "janeiro": "01", "fevereiro": "02", "marco": "03",
                "abril": "04", "maio": "05", "junho": "06",
                "julho": "07", "agosto": "08", "setembro": "09",
                "outubro": "10", "novembro": "11", "dezembro": "12",
            }
            year_match = re.search(r"\b20\d{2}\b", prompt)
            steps.append({
                "type": "filter",
                "column": "data",
                "operator": "month_year",
                "value": f"{year_match.group(0) if year_match else 'current'}-{months[month_match.group(1)]}",
            })
        company_match = re.search(r"empresa\s+(?:=|igual a)?\s*(\d+)", prompt)
        if company_match:
            steps.append({
                "type": "filter",
                "column": "empresa",
                "operator": "equals",
                "value": company_match.group(1),
            })
        if mentions(prompt, "join"):
            key_match = re.search(
                r"(?:pelo|por|usando)\s+(documento|cnpj|cpf|nf|nota fiscal)",
                prompt,
            )
            key = key_match.group(1) if key_match else "documento"
            steps.append({
                "type": "join",
                "left_key": key,
                "right_key": key,
            })
        formula_match = re.search(
            r"(?:criar coluna\s+)?([a-zà-ú][\wà-ú]*)\s*(?:=|:)\s*([a-zà-ú][\wà-ú]*\s*[+\-*/]\s*[a-zà-ú][\wà-ú]*)|calcular\s+([a-zà-ú][\wà-ú]*)\s*:\s*([a-zà-ú][\wà-ú]*\s*[+\-*/]\s*[a-zà-ú][\wà-ú]*)",
            prompt,
        )
        if formula_match:
            column = formula_match.group(1) or formula_match.group(3)
            formula = formula_match.group(2) or formula_match.group(4)
            steps.append({
                "type": "calculate",
                "column": column,
                "formula": formula,
            })
        elif "criar margem" in prompt or "calcular margem" in prompt:
            steps.append({
                "type": "calculate",
                "column": "margem",
                "formula": "",
            })
        if "resumo" in prompt or "agrupar" in prompt or "totalizar" in prompt:
            steps.append({
                "type": "aggregate",
                "group_by": "empresa" if "empresa" in prompt else "cliente",
            })
        if reconciliation:
            steps.append({"type": "reconcile"})
        elif mentions(prompt, "reconcile"):
            steps.append({"type": "reconcile"})
        if mentions(prompt, "validate"):
            steps.append({"type": "validate"})
        if mentions(prompt, "export"):
            steps.append({"type": "export"})
        return steps

    @classmethod
    def _document_columns(
        cls,
        document_id: str,
    ):

        document = cls.CATALOG.documents.get(
            document_id
        )

        if not document:
            return []

        return document.get(
            "required_columns",
            [],
        )


    @staticmethod
    def _inputs(
        prompt: str,
        reconciliation: bool,
        power_bi: bool,
        file_entities: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:

        if file_entities:
            return file_entities

        extension = MockAIService._preferred_extension(prompt)

        if power_bi and not reconciliation:
            return [
                {
                    "id": "origem",
                    "display_name": "Base de origem",
                    "cli_argument": "--input-file",
                    "extension": extension,
                    "required_columns": [],
                }
            ]

        if any(
            term in prompt
            for term in MockAIService.ANTIFRAUD_TERMS
        ):
            return [
                {
                    "id": "base_antifraude",
                    "display_name": "Base Antifraude",
                    "cli_argument": "--input-file",
                    "extension": extension,
                    "required_columns": MockAIService._document_columns(
                        "base_antifraude"
                    ),
                }
            ]

        return [
            {
                "id": "entrada",
                "display_name": "Arquivo de entrada",
                "cli_argument": "--input-file",
                "extension": extension,
                "required_columns": [],
            }
        ]

    @classmethod
    def _preferred_extension(
        cls,
        prompt: str,
    ) -> str:

        if any(
            term in prompt
            for term in cls.SAP_REPORT_TERMS
        ):
            return cls.DOMAIN_EXTENSIONS["sap"]

        if any(
            term in prompt
            for term in (
                "excel",
                "xlsx",
                "relatorio",
                "planilha",
            )
        ):
            return "xlsx"

        return "csv"