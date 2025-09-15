from django.db import migrations, connection


def drop_frms_newemployee_table(apps, schema_editor):
    vendor = connection.vendor
    table_name = 'frms_newemployee'
    with connection.cursor() as cursor:
        tables = connection.introspection.table_names()
        if table_name not in tables:
            return
        if vendor == 'postgresql':
            cursor.execute('DROP TABLE IF EXISTS frms_newemployee CASCADE;')
        else:
            # MySQL/SQLite
            cursor.execute('DROP TABLE IF EXISTS frms_newemployee;')


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('workflow', '0006_remove_state_allowed_groups_transitionlog_and_more'),
    ]

    operations = [
        migrations.RunPython(drop_frms_newemployee_table, noop),
    ]

