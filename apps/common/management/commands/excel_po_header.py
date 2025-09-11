from django.core.management import BaseCommand, call_command
import json

class Command(BaseCommand):
    help = "Imports"

    def handle(self, *args, **options):
        # Example inputs
        excel_path = "C:/Users/n.mantha/Desktop/datafiles/po_header.xlsx"
        model_label = "common.PurchaseOrder"

        # Example mapping: Excel column names -> model fields
        mapping = {
            "Order": "order",
            # Map supplier by a unique field on BusinessPartner (e.g., code or name)
            # If your Excel column holds the BP code, use "supplier__code"; if it's the name, use "supplier__name".
            # Adjust the left-hand Excel column key to match your sheet.
            "Buy-from Business Partner": "supplier__code",
            # Create or get the related CustomUser by username; if it doesn't exist, it will be created
            # with just the username populated.
            "Buyer": "buyer__username",
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
