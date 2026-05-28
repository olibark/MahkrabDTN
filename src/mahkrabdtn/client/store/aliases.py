from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from uuid import UUID

from mahkrabdtn.helpers.resolve import resolve_aliases_path
from mahkrabdtn.tools.parsing.text import parse_text
from mahkrabdtn.tools.parsing.uuid import parse_uuid


@dataclass(frozen=True, slots=True)
class NodeAlias:
    name: str
    nodeID: UUID

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", parse_alias_name(self.name))
        object.__setattr__(self, "nodeID", parse_uuid(self.nodeID, "nodeID"))

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "nodeID": str(self.nodeID),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "NodeAlias":
        return cls(
            name=parse_text(data["name"], "name"),
            nodeID=parse_uuid(data["nodeID"], "nodeID"),
        )


class NodeAliasBook:
    def __init__(
        self,
        aliases: list[NodeAlias] | None = None,
        path: str | Path | None = None,
    ) -> None:

        self.path = Path(path).expanduser() if path is not None else None
        self._aliases: dict[str, NodeAlias] = {}

        for alias in aliases or []:
            self.set_alias(alias.name, alias.nodeID, save=False)

    @classmethod
    def from_identity_path(cls, identityPath: str | Path) -> "NodeAliasBook":
        return cls.from_path(resolve_aliases_path(identityPath))

    @classmethod
    def from_path(cls, path: str | Path) -> "NodeAliasBook":
        aliasPath = Path(path).expanduser()

        if not aliasPath.exists():
            return cls(path=aliasPath)

        data = json.loads(aliasPath.read_text(encoding="utf-8"))
        if not isinstance(data, dict): raise TypeError("alias book must be a JSON object")

        aliases = [
            NodeAlias.from_dict(item)
            for item in data.get("aliases", [])
        ]

        return cls(aliases=aliases, path=aliasPath)

    def set_alias(self, name: str, nodeID: UUID | str, save: bool = True) -> NodeAlias:
        alias = NodeAlias(name=name, nodeID=parse_uuid(nodeID, "nodeID"))
        self._aliases[normalise_alias_name(alias.name)] = alias

        if save: self.save()

        return alias

    def remove_alias(self, name: str, save: bool = True) -> None:
        aliasKey = normalise_alias_name(name)
        if aliasKey not in self._aliases: raise KeyError(f"unknown alias {name}")

        del self._aliases[aliasKey]

        if save: self.save()

    def resolve_node(self, value: str | UUID) -> UUID:
        if isinstance(value, UUID): return value

        lookupName = normalise_alias_name(value)
        if lookupName in self._aliases: return self._aliases[lookupName].nodeID

        return parse_uuid(value, "nodeID")

    def display_name(self, nodeID: UUID | str) -> str:
        nodeID = parse_uuid(nodeID, "nodeID")

        for alias in self.aliases:
            if alias.nodeID == nodeID: return alias.name

        return shorten_node_id(nodeID)

    @property
    def aliases(self) -> list[NodeAlias]:
        return sorted(self._aliases.values(), key=lambda alias: alias.name.casefold())

    def to_dict(self) -> dict[str, object]:
        return {
            "aliases": [alias.to_dict() for alias in self.aliases],
        }

    def save(self) -> None:
        if self.path is None: return

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def parse_alias_name(value: object) -> str:
    alias = parse_text(value, "alias").strip()
    if not alias: raise ValueError("alias must not be empty")
    if any(character in alias for character in "\r\n\t"):
        raise ValueError("alias must fit on one line")

    return alias


def normalise_alias_name(value: object) -> str:
    return parse_alias_name(value).casefold()


def shorten_node_id(nodeID: UUID | str) -> str:
    return str(parse_uuid(nodeID, "nodeID")).split("-", maxsplit=1)[0]
