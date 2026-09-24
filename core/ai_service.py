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
        intent = self.RESOLVER.resolve_intent(prompt_lower)
        file_entities = self._detect_file_entities(prompt_lower)
        sources = self._detect_sources(prompt_lower, file_entities)
        document_ids = self._document_ids(file_entities)
        profile_metadata = self.RESOLVER.profile_metadata(document_ids)
        profile_metadata["intent"] = intent
        reconciliation = self._is_reconciliation(
            prompt_lower,
            document_ids,
            file_entities,
            profile_metadata,
        )
        consolidation = "consolidate" in intent["operations"]
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
        workbook_requested = "workbook" in prompt_lower or (
            "unico" in prompt_lower and ("excel" in prompt_lower or "arquivo" in prompt_lower)
        )
        execution_plan = execution_plan.model_copy(
            update={
                "intent": self._intent_label(intent),
                "intent_confidence": "alta" if intent.get("explicit") else "baixa",
                "intent_source": ["prompt"] if intent.get("explicit") else [],
                "intent_summary": self._intent_summary(
                    intent,
                    prompt_lower,
                    workbook_requested,
                ),
                "decisions": self._plan_decisions(
                    steps, prompt_lower, resolver_keys, profile_metadata
                ),
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
                "output_details": self._output_details(outputs, intent),
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
        if workbook_requested and len(outputs) > 1:
            manifest_data["output_mode"] = "workbook"
            manifest_data["workbook_sheets"] = list(outputs)
            manifest_data["workbook_name"] = "resultado.xlsx"
            manifest_data["outputs"] = ["resultado.xlsx"]
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
    def _intent_label(intent: dict[str, Any]) -> str:
        labels = {
            "period_comparison": "Comparação de períodos",
            "reconcile": "Conciliação de dados",
            "join": "Relacionamento de bases",
            "consolidate": "Consolidação de dados",
            "aggregate": "Agregação de dados",
            "validate": "Validação de dados",
            "calculate": "Cálculo de indicadores",
            "filter": "Filtragem de dados",
            "export": "Exportação de resultados",
        }
        operations = intent.get("operations", [])
        priority = (
            "period_comparison",
            "reconcile",
            "consolidate",
            "aggregate",
            "calculate",
            "validate",
            "join",
            "filter",
            "export",
        )
        return next((labels[item] for item in priority if item in operations), "Processamento de dados")

    @classmethod
    def _intent_summary(
        cls,
        intent: dict[str, Any],
        prompt: str = "",
        workbook_requested: bool = False,
    ) -> str:
        if (
            "vendas" in prompt
            and re.search(
                r"\b(janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\b",
                prompt,
            )
            and "cliente" in prompt
            and "produto" in prompt
        ):
            summary = (
                "O MELLO entendeu que você deseja analisar vendas de julho, "
                "eliminar registros inválidos, calcular faturamento por cliente e produto, "
                "gerar rankings dos maiores resultados e produzir um resumo executivo "
                "com diagnóstico."
            )
            if workbook_requested:
                summary += " Tudo será entregue em um único arquivo Excel."
            return summary
        label = cls._intent_label(intent).lower()
        operations = intent.get("operations", [])
        if len(operations) > 1:
            summary = (
                f"O MELLO entendeu que você deseja {label}, "
                "aplicar as operações identificadas e gerar os resultados revisáveis."
            )
        else:
            summary = f"O MELLO entendeu que você deseja {label}."
        if workbook_requested:
            summary += " Tudo será entregue em um único arquivo Excel."
        return summary

    @staticmethod
    def _plan_decisions(
        steps: list[dict[str, Any]],
        prompt: str,
        keys: list[str],
        profile_metadata: dict[str, Any],
    ) -> list[dict[str, Any]]:
        decisions = []
        for step in steps:
            operation = step.get("type", step.get("operation", "operação"))
            parameters = {
                key: value
                for key, value in step.items()
                if key not in {"type", "operation", "description", "confidence", "pending_confirmation"}
                and value is not None
            }
            pending = step.get("pending_confirmation", [])
            confidence = step.get("confidence", "alta" if parameters else "baixa")
            source = ["prompt"] if parameters else []
            if keys and operation in {"join", "reconcile", "deduplicate"}:
                source = ["perfil"] if not re.search(r"(?:por|pelo|pela|usando|chave)", prompt) else ["prompt"]
            reasons = {
                "normalize": "padronizar nomes e formatos antes do processamento",
                "deduplicate": "evitar que registros repetidos distorçam os resultados",
                "join": "relacionar as entradas por uma chave informada",
                "reconcile": "comparar ou identificar diferenças entre entradas",
                "aggregate": "consolidar os dados conforme solicitado",
                "calculate": "calcular um indicador solicitado",
                "filter": "restringir os dados conforme o filtro informado",
                "unmatched_records": "identificar registros sem correspondência na base relacionada",
                "validate": "verificar a qualidade dos dados",
                "export": "gerar o resultado solicitado",
            }
            decisions.append({
                "operation": operation,
                "parameters": parameters,
                "confidence": confidence,
                "source": source,
                "reason": reasons.get(operation, "atender à intenção identificada"),
                "pending_confirmation": pending,
            })
        return decisions

    @staticmethod
    def _output_details(outputs: list[str], intent: dict[str, Any]) -> list[dict[str, Any]]:
        reasons = {
            "resumo_executivo.xlsx": "oferecer uma visão gerencial do resultado",
            "nfs_perdidas.xlsx": "listar documentos ausentes entre períodos comparados",
            "nfs_novas.xlsx": "listar documentos novos entre períodos comparados",
            "analise_por_cliente.xlsx": "permitir análise do impacto por grupo",
            "analise_mensal.xlsx": "permitir acompanhamento temporal",
            "top_perdas.xlsx": "destacar os maiores impactos",
            "diagnostico.txt": "registrar riscos e conclusões da análise",
            "conciliacao.xlsx": "entregar registros conciliados",
            "divergencias.xlsx": "entregar registros não conciliados ou divergentes",
            "consolidado.xlsx": "entregar a base consolidada",
            "resultado.xlsx": "entregar o resultado do processamento",
        }
        return [
            {
                "name": output,
                "reason": reasons.get(output, "atender ao output definido no plano"),
                "source": ["prompt"] if intent.get("explicit") else [],
            }
            for output in outputs
        ]

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
        intent = profile_metadata.get("intent", {})
        if intent.get("explicit"):
            return intent["pattern"]
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
        intent = profile_metadata.get("intent", {})
        if intent.get("explicit") and any(
            operation in intent.get("operations", []) for operation in ("reconcile", "join")
        ):
            return "reconcile" in intent.get("operations", [])
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
        intent = profile_metadata.get("intent", {})
        if intent.get("period_comparison"):
            base = "comparacao_" + "_".join(
                MockAIService._document_families(document_ids) or ["periodos"]
            ) + "_periodos"
            return re.sub(r"[^a-z0-9]+", "_", base).strip("_")
        profiles = profile_metadata.get("profiles", [])
        configured_ids = {
            profile.get("project_id")
            for profile in profiles
            if profile.get("project_id")
        }
        if len(configured_ids) == 1 and reconciliation:
            return next(iter(configured_ids))
        if "margem" in prompt and "cliente" in prompt:
            base = "resumo_clientes_vendas"
        elif intent.get("explicit"):
            if "reconcile" in intent["operations"]:
                base = "conciliacao_" + "_".join(
                    MockAIService._document_families(document_ids) or ["arquivos"]
                )
            elif "consolidate" in intent["operations"]:
                base = "consolidacao_dados"
            elif document_ids:
                base = document_ids[0]
            else:
                base = "automacao"
            return re.sub(r"[^a-z0-9]+", "_", base).strip("_")
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
        intent = profile_metadata.get("intent", {})
        if intent.get("period_comparison"):
            families = MockAIService._document_families(document_ids)
            return "Comparacao " + " x ".join(
                family.upper() for family in families
            ) + " entre Periodos"
        profiles = profile_metadata.get("profiles", [])
        configured_names = {
            profile.get("project_name")
            for profile in profiles
            if profile.get("project_name")
        }
        if len(configured_names) == 1 and reconciliation:
            return next(iter(configured_names))
        if "margem" in prompt and "cliente" in prompt:
            return "Análise de Margem por Cliente"
        if intent.get("explicit"):
            if "reconcile" in intent["operations"]:
                return "Conciliacao de Documentos"
            if "consolidate" in intent["operations"]:
                return "Consolidacao de Dados"
            if document_ids:
                return "Automacao " + document_ids[0].replace("_", " ").title()
            return "Automacao Gerada"
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
                    "confidence": typed_step.confidence,
                    "pending_confirmation": typed_step.pending_confirmation,
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
        intent = profile_metadata.get("intent", {})
        if profile_metadata.get("category"):
            return profile_metadata["category"]
        if intent.get("explicit"):
            return "operacional"
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
        intent = (profile_metadata or {}).get("intent", {})
        aggregate_steps = [
            step for step in steps if step.get("type") == "aggregate" and step.get("group_by")
        ]
        top_n_steps = [step for step in steps if step.get("type") == "top_n"]
        if len(aggregate_steps) > 1 or top_n_steps:
            explicit_outputs = [
                f"totais_por_{step['group_by']}.xlsx" for step in aggregate_steps
            ]
            explicit_outputs.extend(
                f"top_{step['limit']}_por_{step['group_by']}.xlsx" for step in top_n_steps
            )
            if "resumo executivo" in prompt:
                explicit_outputs.append("resumo_executivo.xlsx")
            if "diagnostico" in prompt:
                explicit_outputs.append("diagnostico.xlsx")
            if explicit_outputs:
                return explicit_outputs
        if intent.get("period_comparison"):
            return [
                "resumo_executivo.xlsx",
                "nfs_perdidas.xlsx",
                "nfs_novas.xlsx",
                "analise_por_cliente.xlsx",
                "analise_mensal.xlsx",
                "top_perdas.xlsx",
                "diagnostico.txt",
            ]
        if intent.get("explicit") and "consolidate" in intent.get("operations", []):
            return ["consolidado.xlsx"]
        profiles = (profile_metadata or {}).get("profiles", [])
        configured_outputs = next(
            (profile.get("suggested_outputs") for profile in profiles if profile.get("suggested_outputs")),
            None,
        )
        if configured_outputs and not intent.get("explicit"):
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
        intent = (profile_metadata or {}).get("intent", {})
        profile_keys = []
        for profile in (profile_metadata or {}).get("profiles", []):
            for key in profile.get("key_columns", []):
                if key not in profile_keys:
                    profile_keys.append(key)
        if intent.get("period_comparison") or (
            not intent.get("explicit") and "period_comparison" in capabilities
        ):
            profiles = (profile_metadata or {}).get("profiles", [])
            profile = profiles[0] if profiles else {}
            comparison = profile.get("comparison", {})
            return [
                {"type": "normalize"},
                {"type": "deduplicate", "key": comparison.get("key")},
                {
                    "type": "aggregate",
                    "group_by": comparison.get("group_by"),
                    "sum": comparison.get("sum", []),
                    "collect": comparison.get("collect"),
                },
                {"type": "reconcile", "key": comparison.get("key")},
                {"type": "aggregate", "group_by": comparison.get("client_group")},
                {"type": "sort", "column": comparison.get("sort"), "descending": True},
            ]
        steps: list[dict[str, Any]] = []
        if reconciliation or mentions(prompt, "normalize"):
            steps.append({"type": "normalize"})
        if mentions(prompt, "deduplicate"):
            steps.append({"type": "deduplicate"})
        null_columns: list[str] = []
        for null_pattern in (
            r"remov(?:er|a)\s+registros?\s+onde\s+([a-zà-ú][\wà-ú]*)\s+(?:esteja|estiver|est[aá])\s+vazi[oa]",
            r"remov(?:er|a)\s+registros?\s+sem\s+([a-zà-ú][\wà-ú]*)",
        ):
            for null_match in re.finditer(null_pattern, prompt):
                column = null_match.group(1)
                if column not in null_columns:
                    null_columns.append(column)
        if null_columns:
            for column in null_columns:
                steps.append({"type": "remove_nulls", "column": column})
        elif mentions(prompt, "remove_nulls"):
            steps.append({"type": "remove_nulls"})
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
                "column": None,
                "operator": "month_year",
                "value": f"{year_match.group(0) if year_match else 'current'}-{months[month_match.group(1)]}",
                "temporal_filter": month_match.group(1),
                "condition": f"mês = {month_match.group(1)}",
                "confidence": "baixa",
                "pending_confirmation": ["coluna_data"],
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
        unmatched_customer_requested = bool(
            re.search(r"\bvendas\s+sem\s+cliente\s+cadastrado\b", prompt)
        )
        if mentions(prompt, "join") or unmatched_customer_requested:
            key_match = re.search(
                r"(?:pelo|por|usando)\s+(documento|cnpj|cpf|nf|nota fiscal)",
                prompt,
            )
            key = key_match.group(1) if key_match else None
            join_step = {
                "type": "join",
                "left_key": key,
                "right_key": key,
                "key": key,
            }
            if not key:
                join_step.update(
                    confidence="baixa",
                    pending_confirmation=["chave_join"],
                )
            steps.append(join_step)
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
                "formula": None,
                "confidence": "baixa",
                "pending_confirmation": ["formula_calculo"],
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
        value_column = next(
            (column for column in null_columns if column in ("valor", "montante", "total", "preco")),
            None,
        )
        total_by_matches = list(
            re.finditer(
                r"(?:total|faturamento|vendas)\s+por\s+([a-zà-ú][\wà-ú]*)",
                prompt,
            )
        )
        if total_by_matches:
            seen_group_by: list[str] = []
            for total_match in total_by_matches:
                group_by = total_match.group(1)
                if group_by in seen_group_by:
                    continue
                seen_group_by.append(group_by)
                aggregate_step = {"type": "aggregate", "group_by": group_by}
                if value_column:
                    aggregate_step["sum"] = [value_column]
                else:
                    aggregate_step.update(
                        confidence="baixa",
                        pending_confirmation=["coluna_valor"],
                    )
                steps.append(aggregate_step)
        elif (
            "resumo" in prompt
            or "agrupar" in prompt
            or "agrupe por" in prompt
            or "totalizar" in prompt
        ):
            group_by = (
                "empresa"
                if "empresa" in prompt
                else "cliente"
                if "cliente" in prompt
                else None
            )
            aggregate_step = {"type": "aggregate", "group_by": group_by}
            if group_by is None:
                aggregate_step.update(
                    confidence="baixa",
                    pending_confirmation=["agrupamento"],
                )
            steps.append(aggregate_step)
        top_n_groups: set[tuple[int, str]] = set()
        for top_match in re.finditer(
            r"identificar\s+os\s+(\d+)\s+([a-zà-ú][\wà-ú]*?)s?\s+com\s+maior\s+([a-zà-ú][\wà-ú]*)",
            prompt,
        ):
            limit, group_by_word, _metric = top_match.groups()
            group_by_word = group_by_word.rstrip("s")
            top_n_groups.add((int(limit), group_by_word))
            top_step = {
                "type": "top_n",
                "group_by": group_by_word,
                "limit": int(limit),
            }
            if value_column:
                top_step["order_by"] = value_column
            else:
                top_step.update(
                    confidence="baixa",
                    pending_confirmation=["coluna_ordenacao"],
                )
            steps.append(top_step)
        for top_match in re.finditer(
            r"\btop\s+(\d+)\s+([a-zà-ú][\wà-ú]*?)s?\b",
            prompt,
        ):
            limit, group_by_word = top_match.groups()
            group_by_word = group_by_word.rstrip("s")
            if (int(limit), group_by_word) in top_n_groups:
                continue
            top_step = {
                "type": "top_n",
                "group_by": group_by_word,
                "limit": int(limit),
            }
            if value_column:
                top_step["order_by"] = value_column
            else:
                top_step.update(
                    confidence="baixa",
                    pending_confirmation=["coluna_ordenacao"],
                )
            steps.append(top_step)
        if unmatched_customer_requested:
            steps.append({
                "type": "unmatched_records",
                "left_source": "vendas",
                "right_source": "cadastro_clientes",
                "confidence": "baixa",
                "pending_confirmation": ["chave_join"],
            })
        if reconciliation:
            key = (
                profile_keys[0]
                if len(profile_keys) == 1
                else profile_keys
                if profile_keys
                else None
            )
            step = {
                "type": "reconcile",
                "key": key,
            }
            if key is None:
                step.update(
                    confidence="baixa",
                    pending_confirmation=["chave_conciliacao"],
                )
            steps.append({
                **step,
            })
        elif mentions(prompt, "reconcile"):
            key = (
                profile_keys[0]
                if len(profile_keys) == 1
                else profile_keys
                if profile_keys
                else None
            )
            steps.append({
                "type": "reconcile",
                "key": key,
                **(
                    {
                        "confidence": "baixa",
                        "pending_confirmation": ["chave_conciliacao"],
                    }
                    if key is None
                    else {}
                ),
            })
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