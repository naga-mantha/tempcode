from django.core.management import BaseCommand, call_command
import json

class Command(BaseCommand):
    help = "Imports"

    def handle(self, *args, **options):
        # Example inputs
        excel_path = "C:/Users/n.mantha/Desktop/datafiles/planned_orders.xlsx"
        # Import Planned Purchase Orders by default; adjust as needed for production
        model_label = "common.PlannedPurchaseOrder"

        # Example mapping: Excel column names -> model fields
        mapping = {
            "Planned Order": "order",
            "Order Item (child) (child)": "item__code",
            "Order Quantity": "quantity",
            # For split models, 'Order Type' is no longer needed here
            "Buyer": "buyer__username",
            "Buy-from BP": "supplier__code",
            "Planned Start Date": "planned_start_date",
            "Planned Finish Date": "planned_end_date",
            "Required Date": "required_date",
        }

        # Value transforms per column (Excel value -> model value)
        value_map = {}

        # Call the import_excel command programmatically
        call_command(
            "import_excel",
            excel=excel_path,
            model=model_label,
            mapping=json.dumps(mapping),
            value_map=json.dumps(value_map),
            # sheet="Sheet1",           # optional
            log_file="debug.log" # optional
        )
