# Generated by Django 5.2.2 on 2025-07-09 14:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0006_workcenter_unique_work_center'),
        ('workflow', '0005_alter_state_allowed_groups_alter_state_is_end_and_more'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='labor',
            constraint=models.UniqueConstraint(fields=('name',), name='unique_labor_name'),
        ),
    ]
