# Generated by Django 5.2.2 on 2025-07-15 17:09

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0017_rename_required_end_date_productionorderoperation_required_end_and_more'),
        ('workflow', '0005_alter_state_allowed_groups_alter_state_is_end_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='PurchaseOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.CharField(max_length=10)),
                ('state', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='workflow.state')),
                ('workflow', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='workflow.workflow')),
            ],
        ),
        migrations.CreateModel(
            name='PurchaseOrderLine',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('line', models.PositiveIntegerField(blank=True, null=True)),
                ('sequence', models.PositiveIntegerField(blank=True, null=True)),
                ('final_receive_date', models.DateField(blank=True, null=True)),
                ('order', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='common.purchaseorder')),
                ('state', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='workflow.state')),
                ('workflow', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='workflow.workflow')),
            ],
        ),
        migrations.AddConstraint(
            model_name='purchaseorder',
            constraint=models.UniqueConstraint(fields=('order',), name='unique_purchase_order'),
        ),
        migrations.AddConstraint(
            model_name='purchaseorderline',
            constraint=models.UniqueConstraint(fields=('order', 'line', 'sequence'), name='unique_purchase_order_line'),
        ),
    ]
