from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('layout', '0004_remove_layoutblock_layoutblock_col_allowed_values_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='layout',
            name='responsive_layouts',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
