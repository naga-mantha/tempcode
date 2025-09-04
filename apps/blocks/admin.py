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
    list_display = ("source_model", )
    search_fields = ("source_model",)
