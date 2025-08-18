from django.db import migrations, models


def copy_code_to_name(apps, schema_editor):
    Block = apps.get_model('blocks', 'Block')
    for b in Block.objects.all():
        # After rename, 'code' holds the previous 'name'
        if not getattr(b, 'name', None):
            b.name = b.code
            b.save(update_fields=['name'])


class Migration(migrations.Migration):

    dependencies = [
        ('blocks', '0004_blockfilterconfig_unique_filter_config_per_user_block'),
    ]

    operations = [
        migrations.RenameField(
            model_name='block',
            old_name='name',
            new_name='code',
        ),
        migrations.AddField(
            model_name='block',
            name='name',
            field=models.CharField(max_length=255, default=''),
        ),
        migrations.RunPython(copy_code_to_name, reverse_code=migrations.RunPython.noop),
    ]

