from django.contrib import admin
from .models import *

@admin.register(Layout)
class LayoutAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "visibility", )
    search_fields = ("name", "visibility",)

@admin.register(LayoutBlock)
class LayoutBlockAdmin(admin.ModelAdmin):
    list_display = ("layout", "block", "row", "col", "width", "height")
    search_fields = ("row", "col", "width", "height",)