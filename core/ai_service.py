from abc import ABC, abstractmethod
import re
import unicodedata
from typing import Any

from core.manifest_generator import ManifestGenerator
from core.models import AutomationAnalysis, ExecutionPlan, OperationStep
from core.pipeline_catalog import get_operation
from core.pipeline_catalog import mentions
from core.pipeline_validator import PipelineValidator
from core.generic_document_detector import GenericDocumentDetector
from core.document_resolver import DocumentResolver

class AIService(ABC):
    """Contrato para provedores de analise de automacoes."""

    @abstractmethod
    def analyze(self, prompt: str) -> AutomationAnalysis:
        raise NotImplementedError


class MockAIService(AIService):
    """Analisador local deterministico para desenvolvimento e testes."""

    RESOLVER = DocumentResolver()

    RECONCILIATION_TERMS = (
        "compar",
        "concili",
        "diverg",
        "cruz",
        "confront",
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
        profile_metadata = self.RESOLVER.profile_metadata(document_ids)
        reconciliation = self._is_reconciliation(
            prompt_lower,
            document_ids,
            file_entities,
            profile_metadata,
        )
        consolidation = self._is_consolidation(prompt_lower)
        power_bi = self._is_power_bi(prompt_lower)
        pattern = self._pattern(
            prompt_lower,
            reconciliation,
            consolidation,
            power_bi,
            profile_metadata,
        )
        project_id = self._project_id(
            prompt_lower,
            document_ids,
            reconciliation,
            consolidation,
            power_bi,
            profile_metadata,
        )
        project_name = self._project_name(
            prompt_lower,
            document_ids,
            reconciliation,
            consolidation,
            power_bi,
            profile_metadata,
        )
        category = self._category(
            document_ids, reconciliation, power_bi, prompt_lower, profile_metadata
        )
        inputs = self._inputs(
            prompt_lower,
            reconciliation,
            power_bi,
            file_entities,
        )
        steps = self._steps(prompt_lower, reconciliation, profile_metadata)
        outputs = self._outputs(
            document_ids,
            reconciliation,
            consolidation,
            power_bi,
            prompt_lower,
            steps,
            profile_metadata,
        )
        description = normalized_prompt.rstrip(".") + "."
        understanding = self._understanding(inputs, steps, outputs, project_name)
        execution_plan = self._execution_plan(
            inputs=inputs,
            steps=steps,
            outputs=outputs,
            project_name=project_name,
        )
        resolved_profiles = self.RESOLVER.resolve_profiles(prompt_lower)
        resolver_keys = self.RESOLVER.infer_keys(prompt_lower, inputs)
        execution_plan = execution_plan.model_copy(
            update={
                "profiles": [
                    {
                        "id": profile["id"],
                        "name": profile.get("name", profile["id"]),
                    }
                    for profile in resolved_profiles
                ],
                "keys": resolver_keys,
                "risks": (
                    ["Os nomes das colunas devem ser confirmados com os arquivos reais."]
                    if inputs
                    else ["Nenhuma entrada foi identificada."]
                ),
                "open_questions": (
                    ["Confirme as colunas e a chave de negócio antes da execução."]
                    if inputs
                    else ["Quais arquivos devem ser processados?"]
                ),
            }
        )

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
        manifest_data["pattern"] = pattern
        manifest_data["pipeline"] = {
            "operations": [
                OperationStep.model_validate(step).model_dump(mode="json")
                for step in steps
            ]
        }
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
        pipeline_validation = PipelineValidator.validate(manifest_data)

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
            pipeline_validation=pipeline_validation,
            execution_plan=execution_plan,
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
        detected = cls.RESOLVER.source_patterns(prompt)
        for entity in file_entities:
            source = entity["source"]
            if source and source not in detected:
                detected.append(source)
        return detected

    @classmethod
    def _detect_file_entities(cls, prompt: str) -> list[dict[str, Any]]:
        return cls.RESOLVER.detect_file_entities(prompt)

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
        profile_metadata: dict[str, Any],
    ) -> str:
        if profile_metadata.get("pattern"):
            return profile_metadata["pattern"]
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
        profile_metadata: dict[str, Any],
    ) -> bool:
        explicit_reconciliation = any(
            term in prompt
            for term in cls.RECONCILIATION_TERMS
            if term != "cruz"
        )
        known_reconciliation_documents = "reconciliation" in profile_metadata.get(
            "capabilities", []
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
        profile_metadata: dict[str, Any],
    ) -> str:
        profiles = profile_metadata.get("profiles", [])
        configured_id = next(
            (profile.get("project_id") for profile in profiles if profile.get("project_id")),
            None,
        )
        if configured_id:
            base = configured_id
        elif "margem" in prompt and "cliente" in prompt:
            base = "resumo_clientes_vendas"
        elif power_bi and not reconciliation:
            base = "dataset_power_bi"
        elif any(term in prompt for term in MockAIService.ANTIFRAUD_TERMS):
            base = "antifraude"
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
        profile_metadata: dict[str, Any],
    ) -> str:
        profiles = profile_metadata.get("profiles", [])
        configured_name = next(
            (profile.get("project_name") for profile in profiles if profile.get("project_name")),
            None,
        )
        if configured_name:
            return configured_name
        if "margem" in prompt and "cliente" in prompt:
            return "Análise de Margem por Cliente"
        if power_bi and not reconciliation:
            return "Dataset Power BI"
        if any(term in " ".join(document_ids) for term in ("antifraude", "fraude", "risco")):
            return "Antifraude"
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
    def _execution_plan(
        inputs: list[dict[str, Any]],
        steps: list[dict[str, Any]],
        outputs: list[str],
        project_name: str,
    ) -> ExecutionPlan:
        transformations = []
        for index, step in enumerate(steps, start=1):
            typed_step = OperationStep.model_validate(step)
            operation = typed_step.operation
            details = typed_step.parameters
            try:
                description = get_operation(operation).description
            except ValueError:
                description = "Operação detectada."
            transformations.append(
                {
                    "order": index,
                    "operation": operation,
                    "description": description,
                    "parameters": details,
                }
            )

        document_rows = [
            {
                "id": item["id"],
                "name": item.get("display_name", item["id"]),
                "source": item.get("source", "não informado"),
                "format": item.get("extension", "não informado").upper(),
            }
            for item in inputs
        ]
        summary = (
            f"{project_name}: {len(document_rows)} documento(s), "
            f"{len(transformations)} transformação(ões) e "
            f"{len(outputs)} output(s)."
        )
        return ExecutionPlan(
            summary=summary,
            documents=document_rows,
            transformations=transformations,
            outputs=outputs,
        )

    @staticmethod
    def _category(
        document_ids: list[str],
        reconciliation: bool,
        power_bi: bool,
        prompt: str,
        profile_metadata: dict[str, Any],
    ) -> str:
        if profile_metadata.get("category"):
            return profile_metadata["category"]
        if power_bi and not reconciliation:
            return "power_bi"
        if any(term in prompt for term in MockAIService.ANTIFRAUD_TERMS):
            return "risco"
        if reconciliation:
            return "financeiro"
        if any(term in prompt for term in ("financeiro", "faturamento", "pagamento", "fornecedor")):
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
        profile_metadata: dict[str, Any] | None = None,
    ) -> list[str]:
        steps = steps or []
        profiles = (profile_metadata or {}).get("profiles", [])
        configured_outputs = next(
            (profile.get("suggested_outputs") for profile in profiles if profile.get("suggested_outputs")),
            None,
        )
        if configured_outputs:
            return list(configured_outputs)
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
        if not reconciliation and "aggregate" in {
            step["type"] for step in steps
        } and "resumo" in prompt:
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
    def _steps(
        prompt: str,
        reconciliation: bool,
        profile_metadata: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        capabilities = (profile_metadata or {}).get("capabilities", [])
        if "period_comparison" in capabilities:
            profiles = (profile_metadata or {}).get("profiles", [])
            profile = profiles[0] if profiles else {}
            comparison = profile.get("comparison", {})
            return [
                {"type": "normalize"},
                {"type": "deduplicate", "key": comparison.get("key", "documento")},
                {
                    "type": "aggregate",
                    "group_by": comparison.get("group_by", "documento"),
                    "sum": comparison.get("sum", []),
                    "collect": comparison.get("collect", "itens"),
                },
                {"type": "reconcile", "key": comparison.get("key", "documento")},
                {"type": "aggregate", "group_by": comparison.get("client_group", "grupo")},
                {"type": "sort", "column": comparison.get("sort", "saldo"), "descending": True},
            ]
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
                "condition": (
                    f"month(data)={int(months[month_match.group(1)])}"
                    if not year_match
                    else f"month_year(data)={year_match.group(0)}-{months[month_match.group(1)]}"
                ),
            })
        company_match = re.search(r"empresa\s+(?:=|igual a)?\s*(\d+)", prompt)
        if company_match:
            steps.append({
                "type": "filter",
                "column": "empresa",
                "operator": "equals",
                "value": company_match.group(1),
                "condition": f"empresa={company_match.group(1)}",
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
                "key": key,
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
        drop_columns_match = re.search(
            r"(?:remov(?:er|a)|exclu(?:ir|a))\s+(?:as\s+)?colunas?\s+(.+?)(?:\.|$)",
            prompt,
        )
        if drop_columns_match:
            columns = [
                item.strip()
                for item in re.split(r"\s*(?:,| e )\s*", drop_columns_match.group(1))
                if item.strip()
            ]
            steps.append({"type": "drop_columns", "columns": columns})
        rename_match = re.search(
            r"renome(?:ar|ie)\s+([\wà-ú]+)\s+para\s+([\wà-ú]+)",
            prompt,
        )
        if rename_match:
            steps.append({
                "type": "rename_columns",
                "mapping": {rename_match.group(1): rename_match.group(2)},
            })
        fill_nulls_match = re.search(
            r"(?:preencher|substituir)\s+nulos(?:\s+com\s+([^.,]+))?",
            prompt,
        )
        if fill_nulls_match:
            parameters = {}
            if fill_nulls_match.group(1):
                parameters["value"] = fill_nulls_match.group(1).strip()
            steps.append({"type": "fill_nulls", **parameters})
        if mentions(prompt, "sort"):
            sort_match = re.search(r"(?:ordenar|ordenado)\s+por\s+([\wà-ú]+)", prompt)
            steps.append({
                "type": "sort",
                "column": sort_match.group(1) if sort_match else None,
            })
        if (
            "resumo" in prompt
            or "agrupar" in prompt
            or "agrupe por" in prompt
            or "totalizar" in prompt
        ):
            steps.append({
                "type": "aggregate",
                "group_by": "empresa" if "empresa" in prompt else "cliente",
            })
        if reconciliation:
            steps.append({"type": "reconcile", "key": "documento"})
        elif mentions(prompt, "reconcile"):
            steps.append({"type": "reconcile", "key": "documento"})
        if mentions(prompt, "validate"):
            steps.append({"type": "validate"})
        if mentions(prompt, "export"):
            steps.append({"type": "export"})
        return steps

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
                    "required_columns": [],
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
    def _preferred_extension(cls, prompt: str) -> str:
        configured_extension = cls.RESOLVER.preferred_extension(prompt)
        if configured_extension:
            return configured_extension
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