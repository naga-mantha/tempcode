from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("layout", "0007_remove_layout_title_column"),
    ]

    operations = [
        # Drop legacy `notes` column left over from older schema revisions.
        # Current Layout model uses `description` instead.
        migrations.RunSQL(
            sql=(
                "ALTER TABLE layout_layout DROP COLUMN IF EXISTS notes;"
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]

