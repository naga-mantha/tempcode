from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


class FilterResolver(ABC):
    """Translates request params into safe, typed filter payloads."""

    @abstractmethod
    def resolve(self, request) -> Mapping[str, Any]:
        raise NotImplementedError

    # Optional: clean an arbitrary values dict to allowed, typed filters
    def clean(self, values: Mapping[str, Any]) -> Mapping[str, Any]:
        return dict(values or {})

    # Optional: return filter schema for rendering dynamic UIs
    def schema(self) -> Sequence[Dict[str, Any]]:
        return []


class QueryBuilder(ABC):
    """Builds a queryset for the block from resolved filters."""

    @abstractmethod
    def get_queryset(self, filters: Mapping[str, Any]):
        raise NotImplementedError


class ColumnResolver(ABC):
    """Computes allowed column list for a table."""

    @abstractmethod
    def get_columns(self, request) -> Sequence[Dict[str, Any]]:
        """Return column dicts: {key, label} (and optional metadata)."""
        raise NotImplementedError


class Serializer(ABC):
    """Serializes querysets to row dicts given a column definition.

    Implementations may use `user` and `policy` for permission-aware masking.
    """

    @abstractmethod
    def serialize_rows(
        self,
        qs,
        columns: Sequence[Dict[str, Any]],
        *,
        user: Any = None,
        policy: Any = None,
    ) -> Iterable[Dict[str, Any]]:
        raise NotImplementedError


class ExportOptions(ABC):
    """Optional export behavior; placeholder for future use."""

    def get_supported_formats(self) -> List[str]:
        return ["csv"]
