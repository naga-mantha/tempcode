# from apps.production.blocks import (
#     ProductionOrderTableBlock,
#     ProductionOrderOperationTableBlock,
#     ProductionGenericPivot,
# )
# from apps.production.charts import (
#     ProductionOrdersByStatusChart,
#     ProductionOrdersPerItemBarChart,
#     ProductionOrdersPerItemLineChart,
# )
#
#
# def register(registry):
#     """Register production related blocks."""
#
#     registry.register("production_order_table", ProductionOrderTableBlock())
#     registry.register("production_order_operation_table", ProductionOrderOperationTableBlock())
#     registry.register("prod_orders_by_status", ProductionOrdersByStatusChart())
#     registry.register("prod_orders_per_item_bar", ProductionOrdersPerItemBarChart())
#     registry.register("prod_orders_per_item_line", ProductionOrdersPerItemLineChart())
#     registry.register("production_generic_pivot", ProductionGenericPivot())
