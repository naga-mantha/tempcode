from django.contrib import admin
from .models import Layout, LayoutBlock, LayoutFilterConfig

@admin.register(Layout)
class LayoutAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "visibility", )
    search_fields = ("name", "visibility",)

@admin.register(LayoutBlock)
class LayoutBlockAdmin(admin.ModelAdmin):
    list_display = ("layout", "block","col",)
    search_fields = ("col",)

@admin.register(LayoutFilterConfig)
class LayoutFilterConfigAdmin(admin.ModelAdmin):
    list_display = ("layout", "user", "name", "is_default")
    search_fields = ("name",)
