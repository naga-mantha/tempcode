from django.core.management import BaseCommand, call_command
import json

class Command(BaseCommand):
    help = "Imports"

    def handle(self, *args, **options):
        # Example inputs
        excel_path = "C:/Users/n.mantha/Desktop/datafiles/po_lines.xlsx"
        model_label = "common.PurchaseOrderLine"

        # Example mapping: Excel column names -> model fields
        mapping = {
            "Order": "order__order",
            "Line": "line",
            "Line (child)": "sequence",
            "Item (child)": "item__code",
            "Order Date": "order_date",
            "Planned Receipt Date": "initial_receive_date",
            "Confirmed Receipt Date": "supplier_confirmed_date",
            "Changed Receipt Date": "modified_receive_date",
            # "Buyer": "final_receive_date",
            "Ordered Quantity": "total_quantity",
            "Received Quantity": "received_quantity",
            # "Buyer": "back_order",
            "Price": "unit_price",
            "Ordered Quantity (child)": "uom__code",
            "Price (child)": "currency__base_currency",
            # "Buyer": "amount_original_currency",
            # "Buyer": "amount_home_currency",
            "Notes": "comments",
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
