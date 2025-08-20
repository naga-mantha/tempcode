from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("layout", "0006_layoutblock_layout_pos_idx_and_more"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="layoutfilterconfig",
            constraint=models.UniqueConstraint(
                fields=["layout", "user"],
                condition=models.Q(("is_default", True)),
                name="unique_default_layout_filter_per_user",
            ),
        ),
    ]

