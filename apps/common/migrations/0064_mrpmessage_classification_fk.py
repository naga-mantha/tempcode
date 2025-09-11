from django.db import migrations, models
import django.db.models.deletion


def noop_forward(apps, schema_editor):
    # No data to migrate from string to FK expected at this point.
    # If any rows exist with string values, they cannot be auto-mapped safely here.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0063_mrp_reschedule_days_and_mrpmessage_classification"),
    ]

    operations = [
        migrations.AlterField(
            model_name="mrpmessage",
            name="classification",
            field=models.ForeignKey(
                related_name="mrp_messages",
                on_delete=django.db.models.deletion.SET_NULL,
                blank=True,
                null=True,
                to="common.mrprescheduledaysclassification",
                db_index=True,
            ),
        ),
        migrations.RunPython(noop_forward, reverse_code=migrations.RunPython.noop),
    ]

