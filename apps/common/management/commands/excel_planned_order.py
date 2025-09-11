from django.core.management import BaseCommand, call_command
import json

class Command(BaseCommand):
    help = "Imports"

    def handle(self, *args, **options):
        # Example inputs
        excel_path = "C:/Users/n.mantha/Desktop/datafiles/planned_orders.xlsx"
        model_label = "common.PlannedOrder"

        # Example mapping: Excel column names -> model fields
        mapping = {
            "Planned Order": "order",
            "Order Item (child) (child)": "item__code",
            "Order Quantity": "quantity",
            "Order Type": "type",
            "Buyer": "buyer__username",
            "Buy-from BP": "supplier__code",
            "Planned Start Date": "planned_start_date",
            "Planned Finish Date": "planned_end_date",
            "Required Date": "required_date",
        }

        # Value transforms per column (Excel value -> model value)
        value_map = {
            "Order Type": {
                "Planned Production Order": "PPRO",
                "Planned Purchase Order": "PPUR",
            }
        }

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
