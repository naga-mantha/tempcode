from django_bi.blocks.registry import block_registry
from django_bi.blocks.models.block_filter_layout import BlockFilterLayout
from django_bi.blocks.services.blocks_filter_utils import FilterResolutionMixin
from django_bi.layout.models import Layout
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
        """Aggregate filter schema, limited to fields chosen in per-user BlockFilterLayout.

        For each block on the layout, we fetch the user's BlockFilterLayout and
        collect the field keys referenced in its sections/rows. Only those keys
        are included from the block's filter schema for the sidebar. If the user
        has no layout for a block, that block contributes no fields to the
        sidebar filters.
        """
        def _keys_from_layout_dict(layout_dict):
            keys = set()
            if not isinstance(layout_dict, dict):
                return keys
            try:
                for sec in (layout_dict.get("sections") or []):
                    for row in (sec.get("rows") or []):
                        for cell in (row or []):
                            if not isinstance(cell, dict):
                                continue
                            k = cell.get("key")
                            r = cell.get("range")
                            if k:
                                keys.add(str(k))
                            if isinstance(r, (list, tuple)) and len(r) == 2:
                                keys.add(str(r[0]))
                                keys.add(str(r[1]))
            except Exception:
                return keys
            return keys

        raw_schema = {}
        user = request.user
        # self.layout must be set by the view before calling this method
        for lb in self.layout.blocks.select_related("block"):
            block_impl = block_registry.get(lb.block.code)
            if not (block_impl and hasattr(block_impl, "get_filter_schema")):
                continue
            # Fetch user-selected layout for this block
            try:
                user_layout = BlockFilterLayout.objects.filter(block=lb.block, user=user).first()
                allowed_keys = _keys_from_layout_dict(user_layout.layout) if (user_layout and isinstance(user_layout.layout, dict)) else set()
            except Exception:
                allowed_keys = set()
            if not allowed_keys:
                # No user layout for this block -> contribute nothing
                continue
            # Get the block's full schema then filter down to allowed keys
            try:
                schema = block_impl.get_filter_schema(request)
            except TypeError:
                schema = block_impl.get_filter_schema(user)
            schema = schema or {}
            limited = {k: v for k, v in schema.items() if k in allowed_keys}
            raw_schema.update(limited)
        return self._resolve_filter_schema(raw_schema, user)
