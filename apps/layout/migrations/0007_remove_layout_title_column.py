from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("layout", "0006_remove_layout_responsive_layouts"),
    ]

    operations = [
        # The Layout model no longer has a `title` field, but some databases
        # may still carry an old NOT NULL column causing inserts to fail.
        # Drop the stray column if it exists to align DB schema with models.
        migrations.RunSQL(
            sql=(
                "ALTER TABLE layout_layout DROP COLUMN IF EXISTS title;"
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]

