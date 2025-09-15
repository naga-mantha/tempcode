from django.db import migrations, models


def _make_code(name: str) -> str:
    if not name:
        return "UNKNOWN"
    # Uppercase, collapse whitespace, replace spaces with underscore
    code = " ".join(str(name).strip().split())
    return code.upper().replace(" ", "_")[:100]


def backfill_program_code(apps, schema_editor):
    Program = apps.get_model('common', 'Program')
    for prog in Program.objects.all():
        if getattr(prog, 'code', None):
            continue
        prog.code = _make_code(prog.name)
        prog.save(update_fields=['code'])


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0073_itemgrouptype_program_itemgroup_sovalidateaggregate'),
    ]

    operations = [
        migrations.AddField(
            model_name='program',
            name='code',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Program Code'),
        ),
        migrations.RunPython(backfill_program_code, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='program',
            name='code',
            field=models.CharField(max_length=100, verbose_name='Program Code'),
        ),
        migrations.RemoveConstraint(
            model_name='program',
            name='unique_program_name',
        ),
        migrations.AddConstraint(
            model_name='program',
            constraint=models.UniqueConstraint(fields=('code',), name='unique_program_code'),
        ),
    ]
