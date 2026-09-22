from pathlib import Path
import yaml


class DocumentCatalog:

    def __init__(
        self,
        path: str = "knowledge/documents",
    ):
        self.path = Path(path)
        self.documents = self._load()

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