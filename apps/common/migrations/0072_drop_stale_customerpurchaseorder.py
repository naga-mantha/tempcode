from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("common", "0071_remove_plannedorder_buyer_remove_plannedorder_item_and_more"),
    ]

    operations = [
        # Drop the obsolete table if it still exists to remove stale FK constraints
        migrations.RunSQL(
            sql=(
                "DROP TABLE IF EXISTS common_customerpurchaseorder CASCADE;"
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]

