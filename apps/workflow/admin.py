from django.contrib import admin
from .models import *
from apps.workflow.forms.field_perm_level import FieldPermLevelForm

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

@admin.register(WorkflowLog)
class WorkflowLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "user", "transition", "comment", "content_type", )

admin.site.register(FieldPermission)

@admin.register(FieldPermLevel)
class FieldPermLevelAdmin(admin.ModelAdmin):
    form = FieldPermLevelForm
    list_display = ('content_type', 'field_name', 'permlevel')