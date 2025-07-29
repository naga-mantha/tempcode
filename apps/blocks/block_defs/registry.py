from .labor_form import LaborFormBlock
from .labor_table import LaborTableBlock

BLOCK_REGISTRY = {
    block.id: block for block in [
        LaborFormBlock(),
        LaborTableBlock(),
    ]
}
