from dataclasses import dataclass
import re


@dataclass(frozen=True)
class GenericDocument:
    id: str
    display_name: str
    extension: str


class GenericDocumentDetector:
    """Detecta papéis de entrada descritos sem depender do catálogo documental."""

    FORMAT_PATTERNS = {
        "xlsx": ("planilha", "excel", "xlsx"),
        "csv": ("csv",),
        "json": ("json",),
    }

    ROLE_LABELS = {
        "vendas": "Vendas",
        "clientes": "Clientes",
        "pedidos": "Pedidos",
        "estoque": "Estoque",
        "faturamento": "Faturamento",
        "fornecedores": "Fornecedores",
        "produtos": "Produtos",
    }

    ROLE_PATTERN = re.compile(
        r"(?:planilha|arquivo|base|relat[oó]rio|csv|json|excel|xlsx)"
        r"\s+(?:de|do|da)\s+([a-zà-ú][a-zà-ú0-9_-]*)",
        re.IGNORECASE,
    )
    SECOND_ROLE_PATTERN = re.compile(
        r"\b(?:outra|outro)\s+(?:planilha|arquivo|base|csv|json|excel|xlsx)?"
        r"\s*(?:de|do|da)\s+([a-zà-ú][a-zà-ú0-9_-]*)",
        re.IGNORECASE,
    )

    @classmethod
    def detect(cls, prompt: str) -> list[GenericDocument]:
        extension = cls._extension(prompt)
        documents: list[GenericDocument] = []
        for match in cls.ROLE_PATTERN.finditer(prompt):
            role = cls._normalize_role(match.group(1))
            if role in cls.ROLE_LABELS:
                documents.append(
                    GenericDocument(
                        id=role,
                        display_name=cls.ROLE_LABELS[role],
                        extension=extension,
                    )
                )

        for match in cls.SECOND_ROLE_PATTERN.finditer(prompt):
            role = cls._normalize_role(match.group(1))
            if role in cls.ROLE_LABELS:
                documents.append(
                    GenericDocument(role, cls.ROLE_LABELS[role], extension)
                )

        if not documents and cls._mentions_two_inputs(prompt):
            documents = [
                GenericDocument("entrada_1", "Documento 1", extension),
                GenericDocument("entrada_2", "Documento 2", extension),
            ]
        return cls._deduplicate(documents)

    @classmethod
    def _extension(cls, prompt: str) -> str:
        for extension, patterns in cls.FORMAT_PATTERNS.items():
            if any(pattern in prompt for pattern in patterns):
                return extension
        return "csv"

    @staticmethod
    def _normalize_role(role: str) -> str:
        return role.lower()

    @staticmethod
    def _mentions_two_inputs(prompt: str) -> bool:
        return bool(
            re.search(
                r"\b(dois|duas|2)\s+(?:arquivos?|documentos?|csvs?|bases?)",
                prompt,
                re.IGNORECASE,
            )
        )

    @staticmethod
    def _deduplicate(documents: list[GenericDocument]) -> list[GenericDocument]:
        unique: list[GenericDocument] = []
        seen: set[str] = set()
        for document in documents:
            if document.id not in seen:
                unique.append(document)
                seen.add(document.id)
        return unique