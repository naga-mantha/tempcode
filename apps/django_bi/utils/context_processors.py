"""Context processors supporting Django BI layouts."""
from __future__ import annotations

from apps.django_bi.layout.models import Layout

__all__ = ["sidebar_layouts"]


def sidebar_layouts(request):
    """Provide layout lists for the global sidebar."""
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {
            "private_layouts": [],
            "public_layouts": [],
        }
    private_qs = Layout.objects.filter(
        user=request.user, visibility=Layout.VISIBILITY_PRIVATE
    ).order_by("category", "name")
    public_qs = Layout.objects.filter(visibility=Layout.VISIBILITY_PUBLIC).order_by(
        "category", "name"
    )
    return {
        "private_layouts": list(private_qs),
        "public_layouts": list(public_qs),
    }
