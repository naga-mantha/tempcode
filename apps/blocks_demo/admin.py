"""Admin registrations for the Blocks Demo app."""

from django.contrib import admin

from . import models


@admin.register(models.DemoBlock)
class DemoBlockAdmin(admin.ModelAdmin):
    """Admin configuration for demo blocks."""

    list_display = ("name", "description")
    search_fields = ("name",)
