from django.contrib import admin
from .models import Layout, LayoutBlock, LayoutFilterConfig

@admin.register(Layout)
class LayoutAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "visibility", )
    search_fields = ("name", "visibility",)
    list_filter = ("visibility",)

@admin.register(LayoutBlock)
class LayoutBlockAdmin(admin.ModelAdmin):
    list_display = ("layout", "block", "col_span", "row_span")
    search_fields = ("block__name", "block__code", "layout__name")

@admin.register(LayoutFilterConfig)
class LayoutFilterConfigAdmin(admin.ModelAdmin):
    list_display = ("layout", "user", "name", "is_default")
    search_fields = ("name",)
