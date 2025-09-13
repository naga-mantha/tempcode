from django.core.management.base import BaseCommand
from django.db.models import F
from django.db.models.functions import Coalesce

from apps.common.models import PurchaseOrderLine


class Command(BaseCommand):
    help = (
        "Fill PurchaseOrderLine.back_order = total_quantity - received_quantity. "
        "Treats NULLs as 0 for the calculation."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--only-open",
            action="store_true",
            help="Update only lines with status='open'",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show how many rows would be updated without writing",
        )

    def handle(self, *args, **options):
        qs = PurchaseOrderLine.objects.all()
        if options.get("only_open"):
            qs = qs.filter(status="open")

        count = qs.count()
        if options.get("dry_run"):
            self.stdout.write(f"{count} PurchaseOrderLine rows would be updated.")
            return

        updated = qs.update(
            back_order=Coalesce(F("total_quantity"), 0.0) - Coalesce(F("received_quantity"), 0.0)
        )
        self.stdout.write(self.style.SUCCESS(f"Updated back_order for {updated} PurchaseOrderLine rows (out of {count})."))

