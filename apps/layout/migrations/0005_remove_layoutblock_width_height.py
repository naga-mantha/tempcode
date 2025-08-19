from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("layout", "0004_layoutblock_ordering_and_position"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="layoutblock",
            name="width",
        ),
        migrations.RemoveField(
            model_name="layoutblock",
            name="height",
        ),
    ]

