# Generated manually to bundle demo Item models with the Blocks app.
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("blocks", "0013_alter_block_enabled_alter_block_override_display"),
    ]

    operations = [
        migrations.CreateModel(
            name="ItemGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=100, unique=True)),
                ("description", models.CharField(blank=True, default="", max_length=255)),
            ],
            options={
                "ordering": ["code"],
                "verbose_name": "Item Group",
                "verbose_name_plural": "Item Groups",
            },
        ),
        migrations.CreateModel(
            name="ItemType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=100, unique=True)),
                ("description", models.CharField(blank=True, default="", max_length=255)),
            ],
            options={
                "ordering": ["code"],
                "verbose_name": "Item Type",
                "verbose_name_plural": "Item Types",
            },
        ),
        migrations.CreateModel(
            name="Item",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=100, unique=True)),
                ("description", models.CharField(blank=True, default="", max_length=255)),
                (
                    "item_group",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="items",
                        to="blocks.itemgroup",
                    ),
                ),
                (
                    "type",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="items",
                        to="blocks.itemtype",
                    ),
                ),
            ],
            options={
                "ordering": ["code"],
                "verbose_name": "Item",
                "verbose_name_plural": "Items",
            },
        ),
    ]
