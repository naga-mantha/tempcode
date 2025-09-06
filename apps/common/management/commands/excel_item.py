from django.core.management import BaseCommand, call_command
import json

class Command(BaseCommand):
    help = "Imports Items via the import_excel command with a predefined mapping."

    def handle(self, *args, **options):
        # Example inputs
        excel_path = "C:/Users/n.mantha/Desktop/datafiles/items.xlsx"
        model_label = "common.Item"

        # Example mapping: Excel column names -> model fields
        mapping = {
            "Item (child)": "code",
            "Description": "description",
        }

        # Call the import_excel command programmatically
        call_command(
            "import_excel",
            excel=excel_path,
            model=model_label,
            mapping=json.dumps(mapping),
            # sheet="Sheet1",           # optional
            log_file="debug.log" # optional
        )