from django.contrib import admin
from .models import *

@admin.register(NewEmployee)
class NewEmployeeAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "submitted_by", )
    search_fields = ("first_name", "last_name",)
