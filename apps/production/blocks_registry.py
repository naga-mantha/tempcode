from apps.production.blocks import ProductionOrderTableBlock
from apps.blocks.registry import register_block

register_block("production_order_table", ProductionOrderTableBlock())