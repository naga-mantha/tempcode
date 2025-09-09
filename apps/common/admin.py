from django.contrib import admin
from .models import *

@admin.register(BusinessPartner)
class BusinessPartnerAdmin(admin.ModelAdmin):
    list_display = ("code", "name",)
    search_fields = ("code", "name",)

@admin.register(CalendarDay)
class CalendarDayAdmin(admin.ModelAdmin):
    list_display = ("calendar", "date",)
    search_fields = ("date",)

@admin.register(CalendarShift)
class CalendarShiftAdmin(admin.ModelAdmin):
    list_display = ("calendar_day", "shift_template",)
    # search_fields = ("date",)

@admin.register(Calendar)
class CalendarAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)

@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ("base_currency", "quote_currency", "price")
    search_fields = ("base_currency", "quote_currency",)

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("code", "description", )
    search_fields = ("code", "description",)

@admin.register(Labor)
class LaborAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "workcenter", "calendar", )
    search_fields = ("code", "name",)

@admin.register(LaborVacation)
class LaborVacationAdmin(admin.ModelAdmin):
    list_display = ("labor", "start_date", "end_date",)
    search_fields = ("start_date", "end_date",)

@admin.register(MachineDowntime)
class MachineDowntimeAdmin(admin.ModelAdmin):
    list_display = ("machine", "start_dt", "end_dt",)
    search_fields = ("start_dt", "end_dt",)

@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "calendar", )
    search_fields = ("code", "name",)

@admin.register(OrderCategory)
class OrderCategoryAdmin(admin.ModelAdmin):
    list_display = ("code", "description", "model_ct", "parent")
    search_fields = ("code", "description",)

@admin.register(ProductionOrderOperation)
class ProductionOrderOperationAdmin(admin.ModelAdmin):
    list_display = ("production_order", "operation", )
    search_fields = ("operation",)

@admin.register(ProductionOrderSchedule)
class ProductionOrderScheduleAdmin(admin.ModelAdmin):
    list_display = ("operation", "start_datetime", "end_datetime", "schedule_state", )
    search_fields = ("start_datetime", "end_datetime", "schedule_state",)

@admin.register(ProductionOrder)
class ProductionOrderAdmin(admin.ModelAdmin):
    list_display = ("production_order", "status", "quantity", "due_date", "item")
    search_fields = ("production_order", "status", "quantity", "due_date",)

@admin.register(PurchaseOrderLine)
class PurchaseOrderLineAdmin(admin.ModelAdmin):
    list_display = ("order", "line", "sequence", "final_receive_date")
    search_fields = ("line", "sequence", "final_receive_date",)

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("order", "buyer", "supplier", "category",)
    search_fields = ("order",)

@admin.register(SalesOrderLine)
class SalesOrderLineAdmin(admin.ModelAdmin):
    list_display = ("order", "line", "sequence",)
    search_fields = ("order", "line", "sequence",)

@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = ("order", "customer", "category",)
    search_fields = ("order",)

@admin.register(ShiftTemplate)
class ShiftTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "start_time", "end_time", )
    search_fields = ("name", "start_time", "end_time",)

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("code", "name", )
    search_fields = ("code", "name",)

@admin.register(UOM)
class UOMAdmin(admin.ModelAdmin):
    list_display = ("code", "name", )
    search_fields = ("code", "name",)

@admin.register(WorkCenter)
class WorkCenterAdmin(admin.ModelAdmin):
    list_display = ("code", "name", )
    search_fields = ("code", "name",)


@admin.register(ToDo)
class ToDoAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "priority", "created_at", "updated_at")
    list_filter = ("status",)
    search_fields = ("title", "description")
    filter_horizontal = ("dependencies",)


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ("number", "created_at", "updated_at")
    search_fields = ("number",)


@admin.register(ReceiptLine)
class ReceiptLineAdmin(admin.ModelAdmin):
    list_display = (
        "receipt",
        "line",
        "po_line",
        "receipt_date",
        "days_offset",
        "classification",
        "amount_home_currency",
    )
    list_filter = ("receipt_date", "classification")
    search_fields = ("receipt__number",)


@admin.register(PurchaseTimelinessClassification)
class PurchaseTimelinessClassificationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "priority",
        "active",
        "counts_for_ontime",
        "min_days",
        "min_inclusive",
        "max_days",
        "max_inclusive",
        "color",
    )
    list_filter = ("active",)
    search_fields = ("name",)
    ordering = ("priority", "id")


@admin.register(PurchaseSettings)
class PurchaseSettingsAdmin(admin.ModelAdmin):
    list_display = ("otd_target_percent",)


@admin.register(GlobalSettings)
class GlobalSettingsAdmin(admin.ModelAdmin):
    list_display = ("fiscal_year_start_month", "fiscal_year_start_day")
