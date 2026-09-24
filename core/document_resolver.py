from __future__ import annotations

import re
from typing import Any

from core.document_catalog import DocumentCatalog
from core.generic_document_detector import GenericDocumentDetector
from core.models import ExecutionPlan
from core.document_engine import FileEntity
from core.pipeline_catalog import get_operation, mentions


class DocumentResolver:
    """Resolves document profiles and generic pipeline intent from a prompt."""

    def __init__(self, catalog: DocumentCatalog | None = None):
        self.catalog = catalog or DocumentCatalog()

    def detect_documents(self, prompt: str) -> list[dict[str, Any]]:
        profiles = self.catalog.resolve_profiles(prompt)
        profile_documents = [
            {
                "id": profile["id"],
                "display_name": profile.get("name", profile["id"]),
                "source": profile.get("source"),
                "extension": (profile.get("accepted_extensions") or ["csv"])[0],
            }
            for profile in profiles
        ]
        generic_documents = [
            {
                "id": document.id,
                "display_name": document.display_name,
                "source": "generic",
                "extension": document.extension,
            }
            for document in GenericDocumentDetector.detect(prompt)
        ]
        return self._merge_prompt_documents(
            profile_documents,
            generic_documents,
            prompt,
        )

    def resolve_profiles(self, prompt: str) -> list[dict[str, Any]]:
        return self.catalog.resolve_profiles(prompt)

    def detect_file_entities(self, prompt: str) -> list[dict[str, Any]]:
        profile_entities: list[dict[str, Any]] = []
        profiles = self.resolve_profiles(prompt)
        for profile in profiles:
            definition = self.catalog.definitions[profile["id"]]
            if "_" in profile["id"] and profile.get("qualifier_strategy") == "context":
                qualifiers = [""]
            else:
                qualifiers = self._qualifiers(profile, prompt)
            for qualifier in qualifiers or [""]:
                file_id = profile["id"]
                if qualifier:
                    file_id = f"{file_id}_{qualifier}"
                profile_entities.append(
                    self._file_entity(
                        profile=profile,
                        definition=definition,
                        file_id=file_id,
                        qualifier=qualifier,
                    )
                )

        generic_entities = [
            self._file_entity(
                profile={
                    "id": document.id,
                    "name": document.display_name,
                    "source": "generic",
                    "accepted_extensions": [document.extension],
                    "required_columns": [],
                    "critical_columns": [],
                },
                definition=None,
                file_id=document.id,
            )
            for document in GenericDocumentDetector.detect(prompt)
        ]
        return self._merge_prompt_documents(
            profile_entities,
            generic_entities,
            prompt,
        )

    def source_patterns(self, prompt: str) -> list[str]:
        sources = []
        for profile in self.resolve_profiles(prompt):
            source = profile.get("source")
            if source and source not in sources:
                sources.append(source)
        return sources

    def resolve_intent(self, prompt: str) -> dict[str, Any]:
        """Resolve user intent without consulting document profiles."""
        normalized = prompt.casefold()
        operations: list[str] = []
        aliases = {
            "reconcile": ("compar", "concili", "diverg", "confront"),
            "join": ("juntar", "unir", "relacionar"),
            "consolidate": ("consolidar", "unificar", "consolidado"),
            "filter": ("filtrar", "somente", "apenas"),
            "validate": ("validar", "validacao", "conferir"),
            "aggregate": ("agrupar", "agrupe", "totalizar", "resumo"),
            "calculate": ("calcular", "criar coluna", "formula"),
            "export": ("exportar", "gerar arquivo", "salvar resultado"),
        }
        for operation, terms in aliases.items():
            if any(term in normalized for term in terms):
                operations.append(operation)
        if "cruz" in normalized and "ambas" in normalized:
            operations.append("reconcile")
        elif "cruz" in normalized:
            operations.append("join")
        period_comparison = (
            "reconcile" in operations
            and any(term in normalized for term in ("period", "mes", "antigo", "novo"))
        )
        if period_comparison:
            operations.insert(0, "period_comparison")
        if "reconcile" in operations:
            pattern = "reconciliation"
        elif "consolidate" in operations or "aggregate" in operations:
            pattern = "consolidation"
        elif "validate" in operations:
            pattern = "validation"
        else:
            pattern = "generic"
        return {
            "operations": operations,
            "explicit": bool(operations),
            "period_comparison": period_comparison,
            "pattern": pattern,
        }

    def preferred_extension(self, prompt: str) -> str | None:
        profiles = self.resolve_profiles(prompt)
        for profile in profiles:
            extensions = profile.get("accepted_extensions", [])
            if extensions:
                return extensions[0]
        return None

    def profile_metadata(self, document_ids: list[str]) -> dict[str, Any]:
        profiles = [
            self.catalog.get_profile(document_id)
            or self.catalog.get_profile(document_id.split("_", 1)[0])
            for document_id in document_ids
        ]
        profiles = [profile for profile in profiles if profile]
        capabilities: list[str] = []
        for profile in profiles:
            for capability in profile.get("capabilities", []):
                if capability not in capabilities:
                    capabilities.append(capability)
        return {
            "profiles": profiles,
            "capabilities": capabilities,
            "category": next(
                (profile.get("category") for profile in profiles if profile.get("category")),
                None,
            ),
            "pattern": next(
                (profile.get("pattern") for profile in profiles if profile.get("pattern")),
                None,
            ),
        }

    @staticmethod
    def _qualifiers(profile: dict[str, Any], prompt: str) -> list[str]:
        strategy = profile.get("qualifier_strategy")
        if strategy != "context":
            return []
        aliases = profile.get("aliases", [])
        matches = list(
            re.finditer(
                r"(?:" + "|".join(re.escape(alias) for alias in aliases) + r")",
                prompt,
                re.IGNORECASE,
            )
        )
        qualifiers: list[str] = []
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(prompt)
            context = prompt[match.end():min(end, match.end() + 40)]
            qualifier = DocumentResolver._clean_qualifier(context, profile)
            if qualifier and qualifier not in qualifiers:
                qualifiers.append(qualifier)
        if len(qualifiers) >= 2:
            return qualifiers
        if profile.get("duplicate_for_qualifier_tokens"):
            configured = [
                token
                for token in profile.get("qualifier_tokens", [])
                if re.search(rf"\b{re.escape(token)}\b", prompt, re.IGNORECASE)
            ]
            if len(configured) >= 2:
                return configured
        if profile.get("duplicate_for_two_reports") and re.search(
            r"\b(dois|duas|2)\s+relat", prompt, re.IGNORECASE
        ):
            return ["antigo", "novo"]
        return qualifiers

    @staticmethod
    def _clean_qualifier(value: str, profile: dict[str, Any]) -> str:
        value = re.sub(r"\b(?:e|outro|do|de|mes)\b", " ", value.casefold())
        month_match = re.search(r"\b(?:mes\s*)?(\d{1,2})\b", value)
        if month_match and profile.get("qualifier_months", True):
            return f"mes_{month_match.group(1)}"
        for token in profile.get("qualifier_tokens", []):
            if re.search(rf"\b{re.escape(token)}\b", value):
                return token
        return ""

    @staticmethod
    def _file_entity(
        profile: dict[str, Any],
        definition: Any,
        file_id: str,
        qualifier: str = "",
    ) -> dict[str, Any]:
        extension = (profile.get("accepted_extensions") or ["csv"])[0]
        entity = FileEntity(
            id=file_id,
            display_name=(
                f"{profile.get('name', file_id)} {qualifier.replace('_', ' ').title()}".strip()
                if qualifier
                else profile.get("name", file_id)
            ),
            document_id=profile.get("id", file_id),
            extension=extension,
            cli_argument=f"--{file_id.replace('_', '-')}" ,
            required_columns=list(profile.get("required_columns", [])),
            critical_columns=list(profile.get("critical_columns", [])),
            attributes={"qualifier": qualifier} if qualifier else {},
            source=profile.get("source"),
        )
        return entity.as_dict()

    @staticmethod
    def _deduplicate_entities(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        unique: list[dict[str, Any]] = []
        seen: set[str] = set()
        for entity in entities:
            if entity["id"] not in seen:
                unique.append(entity)
                seen.add(entity["id"])
        return unique

    def _merge_prompt_documents(
        self,
        profile_documents: list[dict[str, Any]],
        generic_documents: list[dict[str, Any]],
        prompt: str,
    ) -> list[dict[str, Any]]:
        """Preserve every prompt input while preferring catalog metadata on duplicates."""
        if profile_documents and {
            document["id"] for document in generic_documents
        } <= {"entrada_1", "entrada_2"}:
            generic_documents = []
        merged = list(profile_documents)
        profile_roles = {
            role
            for document in profile_documents
            for role in document["id"].split("_")
        }
        merged.extend(
            document
            for document in generic_documents
            if document["id"] not in profile_roles
        )
        merged = self._deduplicate_entities(merged)
        return sorted(
            merged,
            key=lambda document: self._prompt_position(document, prompt),
        )

    def _prompt_position(self, document: dict[str, Any], prompt: str) -> int:
        profile = self.catalog.get_profile(document["id"])
        candidates = [document["id"].replace("_", " "), document.get("display_name", "")]
        if profile:
            candidates.extend(profile.get("aliases", []))
        positions = [
            prompt.casefold().find(candidate.casefold())
            for candidate in candidates
            if candidate and prompt.casefold().find(candidate.casefold()) >= 0
        ]
        return min(positions, default=len(prompt))

    def infer_keys(
        self,
        prompt: str,
        documents: list[dict[str, Any]] | None = None,
    ) -> list[str]:
        keys: list[str] = []
        for profile in self.resolve_profiles(prompt):
            for key in profile.get("key_columns", []):
                if key not in keys:
                    keys.append(key)

        key_match = re.search(
            r"(?:por|pelo|pela|usando|chave(?: principal)?(?: de)?)[\s:]+"
            r"([\wà-ú][\wà-ú ]*)",
            prompt.casefold(),
        )
        if key_match:
            candidate = key_match.group(1).strip(" .,:;")
            if candidate and candidate not in keys:
                keys.append(candidate)
        return keys

    def infer_operations(self, prompt: str) -> list[dict[str, Any]]:
        operations: list[dict[str, Any]] = []
        for operation in (
            "normalize",
            "deduplicate",
            "join",
            "reconcile",
            "aggregate",
            "calculate",
            "filter",
            "sort",
            "validate",
            "export",
        ):
            if mentions(prompt.casefold(), operation):
                definition = get_operation(operation)
                operations.append(
                    {
                        "operation": operation,
                        "description": definition.description,
                        "parameters": {},
                    }
                )
        return operations

    def build_execution_plan(
        self,
        prompt: str,
        *,
        documents: list[dict[str, Any]] | None = None,
        outputs: list[str] | None = None,
    ) -> ExecutionPlan:
        resolved_documents = documents or self.detect_documents(prompt)
        profiles = self.resolve_profiles(prompt)
        keys = self.infer_keys(prompt, resolved_documents)
        operations = self.infer_operations(prompt)
        risks: list[str] = []
        questions: list[str] = []
        if len(resolved_documents) > 1 and not keys:
            questions.append("Qual chave deve relacionar os documentos?")
        if not resolved_documents:
            risks.append("Nenhum documento foi identificado automaticamente.")
        if not outputs:
            questions.append("Quais outputs devem ser gerados?")

        transformations = [
            {
                "order": index,
                "operation": item["operation"],
                "description": item["description"],
                "parameters": item["parameters"],
            }
            for index, item in enumerate(operations, start=1)
        ]
        output_names = outputs or ["resultado.xlsx"]
        return ExecutionPlan(
            summary=(
                f"{len(resolved_documents)} documento(s), "
                f"{len(transformations)} operação(ões) e "
                f"{len(output_names)} output(s)."
            ),
            documents=resolved_documents,
            profiles=[
                {
                    "id": profile["id"],
                    "name": profile.get("name", profile["id"]),
                }
                for profile in profiles
            ],
            transformations=transformations,
            keys=keys,
            outputs=output_names,
            risks=risks,
            open_questions=questions,
        )