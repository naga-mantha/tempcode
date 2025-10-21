from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("blocks", "0008_add_spacer_block"),
    ]

    operations = [
        migrations.DeleteModel(
            name="RepeaterConfig",
        ),
        migrations.DeleteModel(
            name="RepeaterConfigTemplate",
        ),
    ]
