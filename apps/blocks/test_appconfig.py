import sys
from importlib import import_module
from django.test import SimpleTestCase, override_settings

from apps.blocks.apps import BlocksConfig
from apps.blocks.registry import block_registry


class BlocksConfigReadyTests(SimpleTestCase):
    def setUp(self):
        block_registry._blocks.clear()
        block_registry._metadata.clear()
        sys.modules.pop("apps.blocks.dummy_ready_module", None)
        sys.modules.pop("apps.blocks.dummy_ready_callable", None)

    def tearDown(self):
        block_registry._blocks.clear()
        block_registry._metadata.clear()
        sys.modules.pop("apps.blocks.dummy_ready_module", None)
        sys.modules.pop("apps.blocks.dummy_ready_callable", None)

    def test_ready_loads_entries_from_settings(self):
        entries = [
            "apps.blocks.dummy_ready_module",
            "apps.blocks.dummy_ready_callable:register",
        ]
        with override_settings(BLOCKS=entries):
            config = BlocksConfig("apps.blocks", import_module("apps.blocks"))
            config.ready()

        all_blocks = block_registry.all()
        assert "dummy_module_block" in all_blocks
        assert "dummy_callable_block" in all_blocks
