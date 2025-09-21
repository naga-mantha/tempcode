from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blocks', '0003_blockfilterlayout'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='FilterLayoutTemplate',
            new_name='BlockFilterLayoutTemplate',
        ),
    ]

