from django.contrib import admin
from .models import *
from apps.blocks.models.block_filter_layout import BlockFilterLayout

@admin.register(Block)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "description", )
    search_fields = ("code", "name", "description",)

@admin.register(BlockColumnConfig)
class BlockColumnConfigAdmin(admin.ModelAdmin):
    list_display = ("block", "user", "name", "is_default", "visibility" )
    search_fields = ("name", "is_default",)
    list_filter = ("visibility",)

@admin.register(BlockFilterConfig)
class BlockFilterConfigAdmin(admin.ModelAdmin):
    list_display = ("block", "user", "name", "is_default", "visibility" )
    search_fields = ("name", "is_default",)
    list_filter = ("visibility",)

@admin.register(BlockTableConfig)
class BlockTableConfigAdmin(admin.ModelAdmin):
    list_display = ("block", "user", "name", "is_default", "visibility")
    search_fields = ("name",)
    list_filter = ("visibility",)

@admin.register(FieldDisplayRule)
class FieldDisplayRuleAdmin(admin.ModelAdmin):
    list_display = ("model_label", "field_name", "is_mandatory", "is_excluded" )
    search_fields = ("model_label", "field_name", "is_mandatory", "is_excluded",)

@admin.register(PivotConfig)
class PivotConfigAdmin(admin.ModelAdmin):
    list_display = ("block", "user", "name", "is_default", "visibility")
    search_fields = ("name",)
    list_filter = ("visibility",)

@admin.register(RepeaterConfig)
class RepeaterConfigAdmin(admin.ModelAdmin):
    list_display = ("block", "user", "name")
    search_fields = ("name",)

# Template models (admin-defined defaults)
from apps.blocks.models.config_templates import (
    RepeaterConfigTemplate,
    BlockFilterLayoutTemplate,
)

@admin.register(RepeaterConfigTemplate)
class RepeaterConfigTemplateAdmin(admin.ModelAdmin):
    list_display = ("block", "name", "is_default", "site_key")
    list_filter = ("is_default",)
    search_fields = ("name", "site_key")

@admin.register(BlockFilterLayoutTemplate)
class BlockFilterLayoutTemplateAdmin(admin.ModelAdmin):
    list_display = ("block",)
    search_fields = ("block__code", "block__name")

@admin.register(BlockFilterLayout)
class BlockFilterLayoutAdmin(admin.ModelAdmin):
    list_display = ("block", "user")
    search_fields = ("block__code", "block__name", "user__username")

# (admins above already include visibility)
