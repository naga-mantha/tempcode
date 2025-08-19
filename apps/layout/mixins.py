from apps.blocks.registry import block_registry
from apps.blocks.block_types.table.filter_utils import FilterResolutionMixin
from apps.layout.models import Layout
from django.http import Http404


class LayoutAccessMixin:
    """Shared access helpers for layout views."""

    @staticmethod
    def can_manage(user, layout: Layout) -> bool:
        return bool(
            getattr(user, "is_staff", False)
            or (
                layout.visibility == Layout.VISIBILITY_PRIVATE and layout.user_id == getattr(user, "id", None)
            )
        )

    @staticmethod
    def ensure_detail_access(request, layout: Layout) -> None:
        # Public layouts are viewable by any authenticated user; private only by owner.
        if layout.visibility == Layout.VISIBILITY_PRIVATE and layout.user_id != request.user.id:
            raise Http404()

    @staticmethod
    def ensure_edit_access(request, layout: Layout) -> None:
        # Public layouts editable by staff only; private layouts editable by owner or staff.
        if layout.visibility == Layout.VISIBILITY_PUBLIC and not request.user.is_staff:
            raise Http404()
        if not request.user.is_staff and layout.user_id != request.user.id:
            raise Http404()


class LayoutFilterSchemaMixin(FilterResolutionMixin):
    """Builds a resolved filter schema aggregated from all blocks in a layout."""

    def _build_filter_schema(self, request):
        raw_schema = {}
        # self.layout must be set by the view before calling this method
        for lb in self.layout.blocks.select_related("block"):
            block_impl = block_registry.get(lb.block.code)
            if block_impl and hasattr(block_impl, "get_filter_schema"):
                try:
                    schema = block_impl.get_filter_schema(request)
                except TypeError:
                    schema = block_impl.get_filter_schema(request.user)
                raw_schema.update(schema or {})
        return self._resolve_filter_schema(raw_schema, request.user)

