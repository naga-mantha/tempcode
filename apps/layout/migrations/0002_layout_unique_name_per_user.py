from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("layout", "0001_initial"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="layout",
            constraint=models.UniqueConstraint(
                fields=("user", "name"), name="unique_layout_name_per_user"
            ),
        )
    ]

