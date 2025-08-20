from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("layout", "0008_layoutblock_responsive_cols"),
    ]

    operations = [
        migrations.AddField(
            model_name="layoutblock",
            name="col_xxl",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddConstraint(
            model_name="layoutblock",
            constraint=models.CheckConstraint(
                check=(models.Q(("col_xxl__isnull", True)) | models.Q(("col_xxl__in", (1, 2, 3, 4, 6, 12)))),
                name="layoutblock_col_xxl_allowed_values",
            ),
        ),
    ]

