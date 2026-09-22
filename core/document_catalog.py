from pathlib import Path
from typing import Any
import yaml

from core.document_engine import DocumentDefinition, DocumentMatcher


class DocumentCatalog:

    def __init__(
        self,
        path: str = "knowledge/documents",
    ):
        self.path = Path(path)
        self.documents: dict[str, dict[str, Any]] = self._load()
        self.definitions = {
            document_id: DocumentDefinition.from_mapping(document)
            for document_id, document in self.documents.items()
        }
        self.matcher = DocumentMatcher(list(self.definitions.values()))

    def _load(self) -> dict:
        documents = {}

        for file in self.path.glob("*.yaml"):

            with open(
                file,
                encoding="utf-8",
            ) as f:

                document = yaml.safe_load(f)

            documents[
                document["id"]
            ] = document

        return documents

    def find_by_alias(
        self,
        text: str,
    ) -> dict | None:

        text = text.lower()

        for document in self.documents.values():

            aliases = document.get(
                "aliases",
                [],
            )

            if any(
                alias.lower() in text
                for alias in aliases
            ):
                return document

        return None

    def match(self, text: str) -> list[DocumentDefinition]:
        return self.matcher.match(text)