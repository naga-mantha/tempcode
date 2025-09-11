from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0058_alter_plannedorder_order"),
    ]

    operations = [
        # Add typed relations first
        migrations.AddField(
            model_name="mrpmessage",
            name="pol",
            field=models.OneToOneField(
                related_name="mrp_message",
                on_delete=django.db.models.deletion.PROTECT,
                blank=True,
                null=True,
                to="common.purchaseorderline",
            ),
        ),
        migrations.AddField(
            model_name="mrpmessage",
            name="production_order",
            field=models.OneToOneField(
                related_name="mrp_message",
                on_delete=django.db.models.deletion.PROTECT,
                blank=True,
                null=True,
                to="common.productionorder",
            ),
        ),
        # Remove generic relation fields
        migrations.RemoveField(
            model_name="mrpmessage",
            name="content_type",
        ),
        migrations.RemoveField(
            model_name="mrpmessage",
            name="object_id",
        ),
        # Add exclusivity constraint: exactly one target set
        migrations.AddConstraint(
            model_name="mrpmessage",
            constraint=models.CheckConstraint(
                check=(
                    (Q(pol__isnull=False) & Q(production_order__isnull=True))
                    | (Q(pol__isnull=True) & Q(production_order__isnull=False))
                ),
                name="mrp_message_exactly_one_target",
            ),
        ),
    ]

