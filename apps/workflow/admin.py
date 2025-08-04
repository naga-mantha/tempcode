from django.contrib import admin
from .models import *

@admin.register(Workflow)
class WorkFlowAdmin(admin.ModelAdmin):
    list_display = ("name", )
    search_fields = ("name",)

@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ("name", "workflow", "is_start", "is_end", )
    search_fields = ("name",)

@admin.register(Transition)
class TransitionAdmin(admin.ModelAdmin):
    list_display = ("name", "workflow", "source_state", "dest_state", )
    search_fields = ("name",)
