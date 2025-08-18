from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("layout", "0002_layout_unique_name_per_user"),
    ]

    operations = [
        migrations.AlterField(
            model_name="layout",
            name="slug",
            field=models.SlugField(blank=True),
        ),
        migrations.AddConstraint(
            model_name="layout",
            constraint=models.UniqueConstraint(
                fields=("user", "slug"), name="unique_layout_slug_per_user"
            ),
        ),
    ]

