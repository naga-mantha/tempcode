from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("layout", "0013_alter_layoutblock_note_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="layoutblock",
            old_name="preferred_column_config_name",
            new_name="preferred_setting_name",
        ),
    ]
