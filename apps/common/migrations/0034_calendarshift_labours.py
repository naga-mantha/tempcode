# Generated by Django 5.2.2 on 2025-07-18 18:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0033_remove_labor_unique_labor_name_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='calendarshift',
            name='labours',
            field=models.ManyToManyField(blank=True, related_name='assigned_shifts', to='common.labor'),
        ),
    ]
