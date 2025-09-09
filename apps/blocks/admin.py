from django.contrib import admin
from .models import *

@admin.register(Block)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "description", )
    search_fields = ("code", "name", "description",)

@admin.register(BlockColumnConfig)
class BlockColumnConfigAdmin(admin.ModelAdmin):
    list_display = ("block", "user", "name", "is_default" )
    search_fields = ("name", "is_default",)

@admin.register(BlockFilterConfig)
class BlockFilterConfigAdmin(admin.ModelAdmin):
    list_display = ("block", "user", "name", "is_default" )
    search_fields = ("name", "is_default",)

@admin.register(FieldDisplayRule)
class FieldDisplayRuleAdmin(admin.ModelAdmin):
    list_display = ("model_label", "field_name", "is_mandatory", "is_excluded" )
    search_fields = ("model_label", "field_name", "is_mandatory", "is_excluded",)

@admin.register(PivotConfig)
class PivotConfigAdmin(admin.ModelAdmin):
    list_display = ("block", "user", "name", "is_default")
    search_fields = ("name",)

@admin.register(RepeaterConfig)
class RepeaterConfigAdmin(admin.ModelAdmin):
    list_display = ("block", "user", "name")
    search_fields = ("name",)

# Template models (admin-defined defaults)
from apps.blocks.models.config_templates import (
    FilterConfigTemplate,
    ColumnConfigTemplate,
    PivotConfigTemplate,
    RepeaterConfigTemplate,
)

@admin.register(ColumnConfigTemplate)
class ColumnConfigTemplateAdmin(admin.ModelAdmin):
    list_display = ("block", "name", "is_default", "site_key")
    list_filter = ("is_default",)
    search_fields = ("name", "site_key")

@admin.register(FilterConfigTemplate)
class FilterConfigTemplateAdmin(admin.ModelAdmin):
    list_display = ("block", "name", "is_default", "site_key")
    list_filter = ("is_default",)
    search_fields = ("name", "site_key")

@admin.register(PivotConfigTemplate)
class PivotConfigTemplateAdmin(admin.ModelAdmin):
    list_display = ("block", "name", "is_default", "site_key")
    list_filter = ("is_default",)
    search_fields = ("name", "site_key")

@admin.register(RepeaterConfigTemplate)
class RepeaterConfigTemplateAdmin(admin.ModelAdmin):
    list_display = ("block", "name", "is_default", "site_key")
    list_filter = ("is_default",)
    search_fields = ("name", "site_key")
