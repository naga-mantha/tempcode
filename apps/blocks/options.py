from __future__ import annotations

from typing import Any, Dict


# Allowlist of Tabulator options we accept from spec/request for now
ALLOWED_OPTIONS = {
    "layout": str,  # e.g., 'fitColumns'
    "pagination": (bool, str),  # True/False or 'remote'/'local'
    "paginationMode": str,  # 'remote' | 'local' (Tabulator v6)
    "paginationSize": int,
    "paginationSizeSelector": (list, tuple),
    "movableColumns": bool,
    "initialSort": list,  # [{column, dir}]
    "placeholder": str,
    "height": (int, str),
}


def coerce_value(expected, value):
    if expected is int:
        try:
            return int(value)
        except Exception:
            raise ValueError
    if expected is str:
        return str(value)
    if expected is bool:
        if isinstance(value, bool):
            return value
        if str(value).lower() in {"1", "true", "yes", "on"}:
            return True
        if str(value).lower() in {"0", "false", "no", "off"}:
            return False
        raise ValueError
    if expected in (list, tuple):
        if isinstance(value, (list, tuple)):
            return list(value)
        raise ValueError
    if isinstance(expected, tuple):  # union of types
        for t in expected:
            try:
                return coerce_value(t, value)
            except Exception:
                continue
        raise ValueError
    return value


def merge_table_options(*sources: Dict[str, Any]) -> Dict[str, Any]:
    """Shallow-merge allowlisted Tabulator options from sources left→right."""
    out: Dict[str, Any] = {}
    for src in sources:
        if not src:
            continue
        for k, v in src.items():
            if k not in ALLOWED_OPTIONS:
                continue
            try:
                out[k] = coerce_value(ALLOWED_OPTIONS[k], v)
            except Exception:
                # Skip invalid values
                continue
    return out
