from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0059_mrpmessage_typed_relations"),
    ]

    operations = [
        migrations.AddField(
            model_name="purchaseorderline",
            name="status",
            field=models.CharField(
                choices=[("open", "Open"), ("closed", "Closed")],
                default="open",
                max_length=10,
                db_index=True,
            ),
        ),
    ]

