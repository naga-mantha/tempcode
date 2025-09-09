from django.core.management import BaseCommand, call_command
import json

class Command(BaseCommand):
    help = "Imports"

    def handle(self, *args, **options):
        # Example inputs
        excel_path = "C:/Users/n.mantha/Desktop/datafiles/po_lines_receipts.xlsx"
        model_label = "common.Receipt"

        # Example mapping: Excel column names -> model fields
        mapping = {
            "Receipt Number": "number",
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
