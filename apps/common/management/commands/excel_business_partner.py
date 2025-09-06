from django.core.management import BaseCommand, call_command
import json

class Command(BaseCommand):
    help = "Imports"

    def handle(self, *args, **options):
        # Example inputs
        excel_path = "C:/Users/n.mantha/Desktop/datafiles/business_partners.xlsx"
        model_label = "common.BusinessPartner"

        # Example mapping: Excel column names -> model fields
        mapping = {
            "Business Partner": "code",
            "Business Partner (child)": "name",
            # FK by name
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