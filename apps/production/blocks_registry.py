from apps.production.blocks import (
    ProductionOrderTableBlock,
    ProductionOrderOperationTableBlock,
)
from apps.production.charts import ProductionOrdersByStatusChart, SalesByMonthChart, ActiveUsersOverTimeChart


def register(registry):
    """Register production related blocks."""

    registry.register("production_order_table", ProductionOrderTableBlock())
    registry.register("production_order_operation_table", ProductionOrderOperationTableBlock())
    registry.register("prod_orders_by_status", ProductionOrdersByStatusChart())
    registry.register("sales_by_month", SalesByMonthChart())
    registry.register("active_users_over_time", ActiveUsersOverTimeChart())


