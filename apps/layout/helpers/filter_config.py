from typing import Iterable

from apps.accounts.models.custom_user import CustomUser
from apps.layout.models import Layout, LayoutFilterConfig


def ensure_default_none_filter(layout: Layout, user: CustomUser) -> LayoutFilterConfig:
    """Ensure a 'None' filter exists for the given layout+user.

    Creates a LayoutFilterConfig named 'None' with empty values if missing.
    If it's the first config for that layout+user, mark it as default.
    Returns the existing or created LayoutFilterConfig instance.
    """
    qs = LayoutFilterConfig.objects.filter(layout=layout, user=user)
    existing = qs.filter(name="None").first()
    if existing:
        return existing
    return LayoutFilterConfig.objects.create(
        layout=layout,
        user=user,
        name="None",
        values={},
        is_default=(not qs.exists()),
    )


def ensure_default_none_filters_for_users(
    layout: Layout, users: Iterable[CustomUser]
) -> None:
    """Ensure a 'None' filter exists for each user for the layout."""
    for user in users:
        ensure_default_none_filter(layout, user)

