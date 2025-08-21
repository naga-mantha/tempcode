from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("layout", "0010_layout_description_and_block_titles"),
    ]

    operations = [
        migrations.AddField(
            model_name="layoutblock",
            name="preferred_filter_name",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
    ]

