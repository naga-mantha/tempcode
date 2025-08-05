from django.contrib import admin
from .models import *

@admin.register(Block)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ("name", "description", )
    search_fields = ("name", "description",)

@admin.register(BlockColumnConfig)
class BlockColumnConfigAdmin(admin.ModelAdmin):
    list_display = ("block", "user", "name", "is_default" )
    search_fields = ("name", "is_default",)

@admin.register(BlockFilterConfig)
class BlockFilterConfigAdmin(admin.ModelAdmin):
    list_display = ("block", "user", "name", "is_default" )
    search_fields = ("name", "is_default",)