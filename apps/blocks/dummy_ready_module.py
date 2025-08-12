from apps.blocks.base import BaseBlock
from apps.blocks.registry import block_registry


class DummyModuleBlock(BaseBlock):
    template_name = ""

    def get_config(self, request):
        return {}

    def get_data(self, request):
        return {}


block_registry.register("dummy_module_block", DummyModuleBlock())
