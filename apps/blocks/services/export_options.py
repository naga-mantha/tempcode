from __future__ import annotations

from typing import Any, Dict, List, Sequence


class DefaultExportOptions:
    """Default no-op export options.

    Blocks can override by providing their own class via
    spec.services.export_options.
    """

    def filename(self, spec, fmt: str, request, filters: Dict[str, Any]) -> str | None:
        # None -> export view will build default based on spec id + timestamp
        return None

    def sheet_name(self, spec) -> str | None:
        # None -> use spec.name (trimmed to 31 chars for XLSX)
        return None

    def transform_columns(self, columns: Sequence[Dict[str, Any]], *, request=None, filters=None, spec=None) -> Sequence[Dict[str, Any]]:
        # No changes by default
        return columns

    def transform_rows(self, rows: List[Dict[str, Any]], columns: Sequence[Dict[str, Any]], *, request=None, filters=None, spec=None) -> List[Dict[str, Any]]:
        # No changes by default
        return rows

