from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("layout", "0009_layoutblock_col_xxl"),
    ]

    operations = [
        migrations.AddField(
            model_name="layout",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="layoutblock",
            name="title",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="layoutblock",
            name="note",
            field=models.TextField(blank=True, default=""),
        ),
    ]

