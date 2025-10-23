"""Accounts app configuration entry point."""

from .apps import AccountsConfig

__all__ = ["AccountsConfig"]

# Django < 3.2 compatibility
default_app_config = "apps.accounts.apps.AccountsConfig"
