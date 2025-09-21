from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('layout', '0005_layout_responsive_layouts'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='layout',
            name='responsive_layouts',
        ),
    ]
