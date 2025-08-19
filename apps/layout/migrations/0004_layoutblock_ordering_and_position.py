from django.db import migrations, models


def init_positions(apps, schema_editor):
    LayoutBlock = apps.get_model("layout", "LayoutBlock")
    # Seed position based on existing (row, id) ordering if row exists; else by id
    try:
        blocks = list(LayoutBlock.objects.all().order_by("row", "id"))
    except Exception:
        blocks = list(LayoutBlock.objects.all().order_by("id"))
    for idx, lb in enumerate(blocks):
        lb.position = idx
        lb.save(update_fields=["position"])


class Migration(migrations.Migration):

    dependencies = [
        ("layout", "0003_layout_slug_unique_per_user"),
    ]

    operations = [
        migrations.AddField(
            model_name="layoutblock",
            name="position",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(init_positions, migrations.RunPython.noop),
        migrations.AlterModelOptions(
            name="layoutblock",
            options={"ordering": ["position", "id"]},
        ),
        migrations.RemoveField(
            model_name="layoutblock",
            name="row",
        ),
        migrations.AlterField(
            model_name="layoutblock",
            name="col",
            field=models.PositiveIntegerField(default=12),
        ),
    ]

