"""Admin registrations for the ``django_bi`` app.

This module ensures that all admin registrations defined in the nested
packages are imported when Django's admin autodiscovery runs.
"""

from importlib import import_module

for module_path in (
    "apps.django_bi.blocks.admin",
    "apps.django_bi.layout.admin",
    "apps.django_bi.workflow.admin",
):
    import_module(module_path)
