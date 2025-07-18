# Generated by Django 5.2.2 on 2025-06-13 15:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workflow', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='workflow',
            name='status',
            field=models.CharField(choices=[('active', 'Active'), ('Deprecated', 'Deprecated'), ('inactive', 'Inactive')], default='active', help_text='“Active” allows creation & transitions; “Deprecated” allows transitions only; “Inactive” disallows both.', max_length=10),
        ),
    ]
