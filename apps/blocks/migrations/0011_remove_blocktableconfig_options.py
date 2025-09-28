from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blocks', '0010_blocktableconfig'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='blocktableconfig',
            name='options',
        ),
    ]

