from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DocumentDefinition:
    id: str
    name: str
    aliases: tuple[str, ...] = ()
    source: str | None = None
    accepted_extensions: tuple[str, ...] = ()
    critical_columns: tuple[str, ...] = ()
    required_columns: tuple[str, ...] = ()
    document_family: str | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "DocumentDefinition":
        return cls(
            id=data["id"],
            name=data["name"],
            aliases=tuple(data.get("aliases", ())),
            source=data.get("source"),
            accepted_extensions=tuple(data.get("accepted_extensions", ())),
            critical_columns=tuple(data.get("critical_columns", ())),
            required_columns=tuple(data.get("required_columns", ())),
            document_family=data.get("document_family"),
        )


@dataclass
class FileEntity:
    id: str
    display_name: str
    document_id: str
    extension: str
    cli_argument: str
    required_columns: list[str] = field(default_factory=list)
    critical_columns: list[str] = field(default_factory=list)
    attributes: dict[str, str] = field(default_factory=dict)
    source: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "source": self.source or self.document_id,
            "report": self.document_id,
            "extension": self.extension,
            "cli_argument": self.cli_argument,
            "required_columns": self.required_columns,
            "critical_columns": self.critical_columns,
            "attributes": self.attributes,
        }


class DocumentMatcher:
    def __init__(self, definitions: list[DocumentDefinition]):
        self.definitions = definitions

    def match(self, text: str) -> list[DocumentDefinition]:
        normalized = text.casefold()
        matches = [
            definition
            for definition in self.definitions
            if any(alias.casefold() in normalized for alias in definition.aliases)
        ]
        return sorted(
            matches,
            key=lambda definition: min(
                normalized.find(alias.casefold())
                for alias in definition.aliases
                if alias.casefold() in normalized
            ),
        )