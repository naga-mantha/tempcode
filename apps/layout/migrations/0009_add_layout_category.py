from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("layout", "0008_remove_layout_notes_column"),
    ]

    operations = [
        migrations.AddField(
            model_name="layout",
            name="category",
            field=models.CharField(max_length=255, blank=True, default=""),
        ),
    ]

