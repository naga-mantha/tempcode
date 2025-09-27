from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('blocks', '0009_block_category_block_enabled_block_override_display'),
    ]

    operations = [
        migrations.CreateModel(
            name='BlockTableConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('columns', models.JSONField(default=list)),
                ('options', models.JSONField(default=dict)),
                ('visibility', models.CharField(choices=[('private', 'Private'), ('public', 'Public')], default='private', max_length=7)),
                ('is_default', models.BooleanField(default=False)),
                ('block', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='table_configs', to='blocks.block')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.customuser')),
            ],
        ),
        migrations.AddConstraint(
            model_name='blocktableconfig',
            constraint=models.UniqueConstraint(fields=('block', 'user', 'name'), name='unique_tablecfg_per_user'),
        ),
        migrations.AddConstraint(
            model_name='blocktableconfig',
            constraint=models.UniqueConstraint(condition=models.Q(('is_default', True)), fields=('block', 'user'), name='unique_default_tablecfg_per_user'),
        ),
    ]

