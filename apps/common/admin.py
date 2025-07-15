from django.contrib import admin
from .models import *

@admin.register(ProductionOrderSchedule)
class ProductionOrderScheduleAdmin(admin.ModelAdmin):
    list_display = ("operation", "start_datetime", "end_datetime", "schedule_state", )
    search_fields = ("start_datetime", "end_datetime", "schedule_state",)

@admin.register(ProductionOrder)
class ProductionOrderAdmin(admin.ModelAdmin):
    list_display = ("production_order", "part_no", )
    # search_fields = ("priority",)

@admin.register(ProductionOrderOperation)
class ProductionOrderOperationAdmin(admin.ModelAdmin):
    list_display = ("production_order", "operation", )
    search_fields = ("operation",)

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("code", "description", )
    search_fields = ("code", "description",)

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("code", "name", )
    search_fields = ("code", "name",)

@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "calendar", )
    search_fields = ("code", "name",)

@admin.register(WorkCenter)
class WorkCenterAdmin(admin.ModelAdmin):
    list_display = ("code", "name", )
    search_fields = ("code", "name",)

@admin.register(Labor)
class LaborAdmin(admin.ModelAdmin):
    list_display = ("name", "workcenter", "calendar", )
    search_fields = ("name",)

@admin.register(Calendar)
class CalendarAdmin(admin.ModelAdmin):
    list_display = ("name", )
    search_fields = ("name",)

@admin.register(CalendarDay)
class CalendarDayAdmin(admin.ModelAdmin):
    list_display = ("calendar", "date", )
    search_fields = ("date",)

@admin.register(CalendarShift)
class CalendarShiftAdmin(admin.ModelAdmin):
    list_display = ("calendar_day", "shift_template", )
    # search_fields = ("date",)

@admin.register(ShiftTemplate)
class ShiftTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "start_time", "end_time", )
    search_fields = ("name", "start_time", "end_time",)

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("order", )
    search_fields = ("order",)

@admin.register(PurchaseOrderLine)
class PurchaseOrderLineAdmin(admin.ModelAdmin):
    list_display = ("order", "line", "sequence", "final_receive_date")
    search_fields = ("line", "sequence", "final_receive_date",)

@admin.register(MachineDowntime)
class MachineDowntimeAdmin(admin.ModelAdmin):
    list_display = ("machine", "start_dt", "end_dt",)
    search_fields = ("start_dt", "end_dt",)