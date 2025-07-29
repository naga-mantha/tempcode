from django.contrib import admin
from .models import *


@admin.register(LaborPageLayout)
class LaborPageLayoutAdmin(admin.ModelAdmin):
    list_display = ("user", "name", "is_default", )
    search_fields = ("name", "is_default",)
