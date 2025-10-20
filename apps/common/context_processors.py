from django.conf import settings


def branding(request):
    """Expose company branding values to templates."""
    return {
        "company_full_name": getattr(settings, "COMPANY_FULL_NAME", "Mecaer America Inc."),
    }
