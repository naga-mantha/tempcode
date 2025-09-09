from django.core.management import BaseCommand, call_command
import json

class Command(BaseCommand):
    help = "Imports"

    def handle(self, *args, **options):
        # Example inputs
        excel_path = "C:/Users/n.mantha/Desktop/datafiles/po_lines_receipts.xlsx"
        model_label = "common.ReceiptLine"

        # Example mapping: Excel column names -> model fields
        mapping = {
            # Receipt header and line number
            "Receipt Number": "receipt__number",
            "Receipt Number (child)": "line",

            # Map PO + Line + Squence to the po_line FK via composite lookup
            # Adjust the left-hand keys to match your exact Excel headers
            "Order": "po_line__order__order",
            "Line": "po_line__line",
            "Sequence": "po_line__sequence",

            # Other fields on ReceiptLine
            "Received Quantity": "received_quantity",
            "Actual Receipt Date": "receipt_date",
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
