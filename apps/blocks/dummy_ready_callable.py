from apps.blocks.base import BaseBlock


class DummyCallableBlock(BaseBlock):
    template_name = ""

    def get_config(self, request):
        return {}

    def get_data(self, request):
        return {}


def register(registry):
    registry.register("dummy_callable_block", DummyCallableBlock())
