# apps/blocks/registry.py

BLOCK_REGISTRY = {}

def register_block(block_id, block_instance):
    BLOCK_REGISTRY[block_id] = block_instance

def get_block(block_id):
    return BLOCK_REGISTRY.get(block_id)
