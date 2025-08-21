from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("layout", "0011_layoutblock_preferred_filter_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="layoutblock",
            name="preferred_column_config_name",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
    ]

