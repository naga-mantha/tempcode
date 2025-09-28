from django.contrib import admin
from .models import *
from apps.common.admin_mixins import BaseAutoComputeAdmin
from apps.common.models import ItemGroupType, Program, ItemGroup
from apps.common.models import ItemType

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
    list_display = ("code",)
    search_fields = ("code",)

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

@admin.register(PurchaseOrderCategory)
class PurchaseOrderCategoryAdmin(admin.ModelAdmin):
    list_display = ("code", "description", "parent")
    search_fields = ("code", "description",)

@admin.register(SalesOrderCategory)
class SalesOrderCategoryAdmin(admin.ModelAdmin):
    list_display = ("code", "description", "parent")
    search_fields = ("code", "description",)

@admin.register(ProductionOrderCategory)
class ProductionOrderCategoryAdmin(admin.ModelAdmin):
    list_display = ("code", "description", "parent")
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
class PurchaseOrderLineAdmin(BaseAutoComputeAdmin):
    list_display = ("order", "line", "sequence", "final_receive_date")
    search_fields = ("line", "sequence", "final_receive_date",)
    # To skip back_order recompute on admin save for import-heavy clients,
    # set this to {"back_order"} or override get_auto_compute_save_kwargs.
    # auto_compute_recalc_exclude = {"back_order"}

    def get_auto_compute_save_kwargs(self, request, obj, form, change):
        kwargs = super().get_auto_compute_save_kwargs(request, obj, form, change) or {}
        try:
            from django.conf import settings
            if getattr(settings, "PURCHASE_ADMIN_SKIP_BACK_ORDER_RECALC", False):
                excl = set(kwargs.get("recalc_exclude", set()))
                excl.add("back_order")
                kwargs["recalc_exclude"] = excl
        except Exception:
            pass
        return kwargs

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
    list_display = ("fiscal_year_start_month", "fiscal_year_start_day", "home_currency_code")


@admin.register(PlannedPurchaseOrder)
class PlannedPurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("order", "item", "quantity", "uom", "required_date")
    search_fields = ("order", "item__code", "item__description")


@admin.register(PlannedProductionOrder)
class PlannedProductionOrderAdmin(admin.ModelAdmin):
    list_display = ("order", "item", "quantity", "uom", "required_date")
    search_fields = ("order", "item__code", "item__description")


@admin.register(PurchaseMrpMessage)
class PurchaseMrpMessageAdmin(admin.ModelAdmin):
    list_display = (
        "pol",
        "mrp_message",
        "mrp_reschedule_date",
        "reschedule_delta_days",
        "direction",
        "classification",
    )
    list_filter = ("direction", "mrp_reschedule_date")
    search_fields = ("mrp_message",)


@admin.register(ProductionMrpMessage)
class ProductionMrpMessageAdmin(admin.ModelAdmin):
    list_display = (
        "production_order",
        "mrp_message",
        "mrp_reschedule_date",
        "reschedule_delta_days",
        "direction",
        "classification",
    )
    list_filter = ("direction", "mrp_reschedule_date")
    search_fields = ("mrp_message",)


@admin.register(MrpRescheduleDaysClassification)
class MrpRescheduleDaysClassificationAdmin(admin.ModelAdmin):
    list_display = ("name", "min_days", "max_days")


@admin.register(ItemGroupType)
class ItemGroupTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "description")
    search_fields = ("code", "description")


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "budget")
    search_fields = ("code", "name")


@admin.register(ItemGroup)
class ItemGroupAdmin(admin.ModelAdmin):
    list_display = ("code", "description", "type", "program")
    search_fields = ("code", "description")
    search_fields = ("name",)


@admin.register(ItemType)
class ItemTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "description")
    search_fields = ("code", "description")

@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ("base", "quote", "rate_date", "rate", "source")
    list_filter = ("base", "quote", "rate_date")
    search_fields = ("base__code", "quote__code", "source")


@admin.register(SoValidateAggregate)
class SoValidateAggregateAdmin(admin.ModelAdmin):
    list_display = ("item",)


from apps.common.models import Roadmap


@admin.register(Roadmap)
class RoadmapAdmin(admin.ModelAdmin):
    list_display = ("title", "app", "timeframe", "status")
    list_filter = ("app", "timeframe", "status")
    search_fields = ("title", "description", "technical_specifications")

    
