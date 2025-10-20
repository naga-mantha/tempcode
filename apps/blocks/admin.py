from django.contrib import admin
from .models import *

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

@admin.register(BlockFilterLayoutTemplate)
class BlockFilterLayoutTemplateAdmin(admin.ModelAdmin):
    list_display = ("block",)
    search_fields = ("block__code", "block__name")

@admin.register(BlockFilterLayout)
class BlockFilterLayoutAdmin(admin.ModelAdmin):
    list_display = ("block", "user")
    search_fields = ("block__code", "block__name", "user__username")


@admin.register(Layout)
class LayoutAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "visibility", "is_default", "slug", "created_at")
    search_fields = ("name", "slug", "owner__username")
    list_filter = ("visibility", "is_default")
    autocomplete_fields = ("owner",)


@admin.register(LayoutBlock)
class LayoutBlockAdmin(admin.ModelAdmin):
    list_display = (
        "layout",
        "slug",
        "block",
        "order",
        "row_index",
        "column_index",
    )
    search_fields = ("slug", "layout__name", "block__name", "block__code")
    list_filter = ("layout",)
    autocomplete_fields = ("layout", "block")


@admin.register(LayoutFilterConfig)
class LayoutFilterConfigAdmin(admin.ModelAdmin):
    list_display = ("layout", "owner", "name", "visibility", "is_default")
    search_fields = ("name", "slug", "layout__name", "owner__username")
    list_filter = ("visibility", "is_default")
    autocomplete_fields = ("layout", "owner")
