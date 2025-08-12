from django.db import IntegrityError
from django.test import TestCase

from apps.accounts.models.custom_user import CustomUser
from apps.blocks.models.block import Block
from apps.blocks.models.block_filter_config import BlockFilterConfig


class BlockFilterConfigTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create(username="user")
        self.block = Block.objects.create(name="block")

    def test_unique_constraint_on_block_user_name(self):
        BlockFilterConfig.objects.create(
            block=self.block,
            user=self.user,
            name="default",
            values={"foo": "bar"},
        )

        with self.assertRaises(IntegrityError):
            BlockFilterConfig.objects.create(
                block=self.block,
                user=self.user,
                name="default",
                values={"baz": "qux"},
            )
