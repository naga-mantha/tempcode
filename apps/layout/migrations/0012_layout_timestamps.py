from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("layout", "0011_layoutblock_settings"),
    ]

    operations = [
        migrations.AddField(
            model_name="layout",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, null=True, blank=True),
        ),
        migrations.AddField(
            model_name="layout",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, null=True, blank=True),
        ),
    ]

