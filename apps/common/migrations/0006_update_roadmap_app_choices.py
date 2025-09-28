from django.db import migrations, models


def migrate_blocks_to_table(apps, schema_editor):
    Roadmap = apps.get_model("common", "Roadmap")
    Roadmap.objects.filter(app="Blocks").update(app="Table")


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0005_roadmap"),
    ]

    operations = [
        migrations.RunPython(migrate_blocks_to_table, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="roadmap",
            name="app",
            field=models.CharField(
                choices=[
                    ("Common", "Common"),
                    ("Workflows", "Workflows"),
                    ("Permissions", "Permissions"),
                    ("Layouts", "Layouts"),
                    ("Purchase", "Purchase"),
                    ("Production", "Production"),
                    ("Sales", "Sales"),
                    ("Planning", "Planning"),
                    ("Service", "Service"),
                    ("Table", "Table"),
                    ("Pivot", "Pivot"),
                    ("Pie", "Pie"),
                    ("Bar", "Bar"),
                    ("Line", "Line"),
                    ("Dial", "Dial"),
                    ("Kanban", "Kanban"),
                    ("Gannt", "Gannt"),
                    ("Repeater", "Repeater"),
                    ("Spacer", "Spacer"),
                    ("Text", "Text"),
                    ("Form", "Form"),
                    ("Button", "Button"),
                    ("List", "List"),
                ],
                max_length=20,
            ),
        ),
    ]

