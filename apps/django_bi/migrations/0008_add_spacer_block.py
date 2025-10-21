from django.db import migrations


def create_spacer_block(apps, schema_editor):
    Block = apps.get_model('django_bi', 'Block')
    try:
        Block.objects.get_or_create(
            code='spacer',
            defaults={'name': 'Spacer', 'description': 'Empty block for adding vertical space in layouts.'}
        )
    except Exception:
        pass


def remove_spacer_block(apps, schema_editor):
    Block = apps.get_model('django_bi', 'Block')
    try:
        Block.objects.filter(code='spacer').delete()
    except Exception:
        pass


class Migration(migrations.Migration):
    dependencies = [
        ('django_bi', '0007_blockfilterconfig_visibility_and_more'),
    ]

    operations = [
        migrations.RunPython(create_spacer_block, remove_spacer_block),
    ]

