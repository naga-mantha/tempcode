from __future__ import annotations
from typing import Any, Optional

class PolicyService:
    """Permissive policy facade."""

    def filter_queryset(self, user: Any, qs: Any) -> Any:
        return qs

    def can_read_field(
        self, user: Any, model: Any, field: str, obj: Optional[Any] = None
    ) -> bool:
        return True

    def can_write_field(
        self, user: Any, model: Any, field: str, obj: Optional[Any] = None
    ) -> bool:
        return True

__all__ = ["PolicyService"]
