from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import *

@admin.register(TableViewConfig)
class TableViewConfigAdmin(admin.ModelAdmin):
    list_display = ("title", "table_name", "model_label", )
    search_fields = ("title", "table_name", "model_label",)


@admin.register(UserColumnConfig)
class UserColumnConfigAdmin(admin.ModelAdmin):
    list_display = ("user", "table_config", "name", )
    search_fields = ("name",)

@admin.register(UserFilterConfig)
class UserFilterConfigAdmin(admin.ModelAdmin):
    list_display = ("user", "table_config", "name",)
    search_fields = ("name",)

@admin.register(FieldDisplayRule)
class FieldDisplayRuleAdmin(admin.ModelAdmin):
    list_display = ("model_label", "field_name", "is_mandatory", "is_excluded", )
    search_fields = ("model_label", "field_name",)
