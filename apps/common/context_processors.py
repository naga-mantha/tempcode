from apps.layout.models import Layout
from django.conf import settings


def sidebar_layouts(request):
    """Provide layout lists for the global sidebar.

    - Private layouts: current user's private, ordered by category then name
    - Public layouts: all public, ordered by category then name
    """
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {
            "private_layouts": [],
            "public_layouts": [],
        }
    private_qs = Layout.objects.filter(user=request.user, visibility=Layout.VISIBILITY_PRIVATE).order_by(
        "category", "name"
    )
    public_qs = Layout.objects.filter(visibility=Layout.VISIBILITY_PUBLIC).order_by("category", "name")
    return {
        "private_layouts": list(private_qs),
        "public_layouts": list(public_qs),
    }


def branding(request):
    """Expose company branding values to templates."""
    return {
        "company_full_name": getattr(settings, "COMPANY_FULL_NAME", "Mecaer America Inc."),
    }
