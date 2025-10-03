from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional, Sequence


@dataclass(frozen=True)
class Services:
    filter_resolver: Optional[type] = None
    column_resolver: Optional[type] = None
    query_builder: Optional[type] = None
    serializer: Optional[type] = None
    export_options: Optional[type] = None


@dataclass(frozen=True)
class BlockSpec:
    id: str
    name: str
    kind: Literal["table", "pivot", "chart", "content"]
    template: str
    supported_features: Sequence[str]
    services: Optional[Services] = None
    category: Optional[str] = None
    description: str = ""
    # Optional Tabulator defaults (allowlisted keys only)
    table_options: Optional[dict[str, Any]] = field(default_factory=dict)
    # Generic table helpers (optional, for parameterized services)
    # Django model class for table data (if using generic ModelQueryBuilder)
    model: Optional[type] = None
    # Optional filter schema driving UI + parsing
    # Each item: {key, type, label?, choices?, choices_url?, params?, lookup?/lookups?}
    filter_schema: Optional[Sequence[dict[str, Any]]] = None
    # Column catalog control: how deep to traverse relations when listing fields
    column_max_depth: int = 0
    download_options: Optional[dict[str, Any]] = field(default_factory=dict)
