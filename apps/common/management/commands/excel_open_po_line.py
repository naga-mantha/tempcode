from django.core.management import BaseCommand, call_command
import json

class Command(BaseCommand):
    help = "Imports"

    def handle(self, *args, **options):
        # Example inputs
        excel_path = "C:/Users/n.mantha/Desktop/datafiles/open_po.xlsx"
        model_label = "common.PurchaseOrderLine"

        # Example mapping: Excel column names -> model fields
        mapping = {
            "Order": "order__order",
            "Line": "line",
            "Sequence": "sequence",
            "Item (child)": "item__code",
            "Order Date": "order_date",
            "Planned Receipt Date": "initial_receive_date",
            "Confirmed Receipt Date": "supplier_confirmed_date",
            "Changed Receipt Date": "modified_receive_date",
            "Ordered Quantity": "total_quantity",
            "Received Quantity": "received_quantity",
            "Price": "unit_price",
            # "Ordered Quantity (child)": "uom__code",
            "Price (child)": "currency__code",
            # "Notes": "comments",
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
