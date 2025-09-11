from django.core.management import BaseCommand, call_command
from apps.common.models import PurchaseOrderLine
import pandas as pd
import json

class Command(BaseCommand):
    help = "Imports"

    def handle(self, *args, **options):
        # Example inputs
        excel_path = "C:/Users/n.mantha/Desktop/datafiles/po_lines_receipts.xlsx"
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
            "Price (child)": "currency__base_currency",
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

        # After import, mark all imported lines as closed based on the Excel rows
        try:
            df = pd.read_excel(excel_path, dtype=str, keep_default_na=False)
        except Exception:
            df = None
        if df is not None:
            # Normalize column names
            df.columns = [str(c) for c in df.columns]
            for _, row in df.iterrows():
                order = (row.get("Order") or "").strip()
                line = (row.get("Line") or "").strip()
                sequence = (row.get("Sequence") or "").strip()
                if not order or not line or not sequence:
                    continue
                try:
                    line_no = int(line)
                    seq_no = int(sequence)
                except Exception:
                    continue
                # Update only existing rows created by the import
                PurchaseOrderLine.objects.filter(
                    order__order=order,
                    line=line_no,
                    sequence=seq_no,
                ).update(status="closed")
