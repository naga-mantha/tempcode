from apps.blocks.registry import block_registry
from apps.blocks.block_types.table.filter_utils import FilterResolutionMixin
from apps.layout.models import Layout
from django.http import Http404
from django.shortcuts import get_object_or_404


class LayoutAccessMixin:
    """Shared access helpers for layout views."""

    @staticmethod
    def get_layout(*, username: str, slug: str) -> Layout:
        qs = Layout.objects.prefetch_related("blocks__block", "filter_configs")
        return get_object_or_404(qs, slug=slug, user__username=username)

    @staticmethod
    def can_manage(user, layout: Layout) -> bool:
        return bool(
            getattr(user, "is_staff", False)
            or (
                layout.visibility == Layout.VISIBILITY_PRIVATE and layout.user_id == getattr(user, "id", None)
            )
        )

    @staticmethod
    def can_view(user, layout: Layout) -> bool:
        # Public layouts viewable by any authenticated user; private only by owner.
        return bool(
            layout.visibility == Layout.VISIBILITY_PUBLIC
            or layout.user_id == getattr(user, "id", None)
        )

    @classmethod
    def ensure_access(cls, request, layout: Layout, action: str) -> None:
        """Unified authorization check.

        - action="view": public or owner may view
        - action="edit": staff, or owner when private
        """
        if action == "view":
            if not cls.can_view(request.user, layout):
                raise Http404()
        elif action == "edit":
            if not cls.can_manage(request.user, layout):
                raise Http404()
        else:
            # Unknown action; default to deny
            raise Http404()

    @classmethod
    def ensure_detail_access(cls, request, layout: Layout) -> None:
        # Backward-compatible wrapper using unified check
        cls.ensure_access(request, layout, action="view")

    @classmethod
    def ensure_edit_access(cls, request, layout: Layout) -> None:
        # Backward-compatible wrapper using unified check
        cls.ensure_access(request, layout, action="edit")


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
