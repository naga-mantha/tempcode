from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("layout", "0007_unique_default_layout_filter_per_user"),
    ]

    operations = [
        migrations.AddField(
            model_name="layoutblock",
            name="col_sm",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="layoutblock",
            name="col_md",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="layoutblock",
            name="col_lg",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="layoutblock",
            name="col_xl",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddConstraint(
            model_name="layoutblock",
            constraint=models.CheckConstraint(
                check=(models.Q(("col_sm__isnull", True)) | models.Q(("col_sm__in", (1, 2, 3, 4, 6, 12)))),
                name="layoutblock_col_sm_allowed_values",
            ),
        ),
        migrations.AddConstraint(
            model_name="layoutblock",
            constraint=models.CheckConstraint(
                check=(models.Q(("col_md__isnull", True)) | models.Q(("col_md__in", (1, 2, 3, 4, 6, 12)))),
                name="layoutblock_col_md_allowed_values",
            ),
        ),
        migrations.AddConstraint(
            model_name="layoutblock",
            constraint=models.CheckConstraint(
                check=(models.Q(("col_lg__isnull", True)) | models.Q(("col_lg__in", (1, 2, 3, 4, 6, 12)))),
                name="layoutblock_col_lg_allowed_values",
            ),
        ),
        migrations.AddConstraint(
            model_name="layoutblock",
            constraint=models.CheckConstraint(
                check=(models.Q(("col_xl__isnull", True)) | models.Q(("col_xl__in", (1, 2, 3, 4, 6, 12)))),
                name="layoutblock_col_xl_allowed_values",
            ),
        ),
    ]

