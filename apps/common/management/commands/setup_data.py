from django.core.management.base import BaseCommand
from django.db import transaction

from apps.common.models import (
    ItemGroupType,
    Program,
    Currency,
    ItemType,
    ItemGroup,
    MrpRescheduleDaysClassification,
    PurchaseOrderCategory,
    PurchaseSettings,
    PurchaseTimelinessClassification,
    GlobalSettings,
    UOM,
)


class Command(BaseCommand):
    help = "Seeds ItemGroupType, Program, Currency, ItemType, and ItemGroup records (safe to run multiple times)."

    @transaction.atomic
    def handle(self, *args, **options):
        # Dummy ItemGroupType data
        item_group_types = [
            {"code": "b525", "description": "B525"},
            {"code": "cost", "description": "Cost"},
            {"code": "customer_property", "description": "Customer Property"},
            {"code": "legacy", "description": "Legacy"},
            {"code": "f35", "description": "F35"},
            {"code": "legacy_g_series", "description": "Legacy G Series"},
            {"code": "mro", "description": "MRO"},
            {"code": "not_using", "description": "Not Using"},
            {"code": "npi", "description": "NPI"},
            {"code": "other", "description": "Other"},
            {"code": "slow_moving", "description": "Slow Moving"},

        ]

        # Dummy Program data
        programs = [
            {"name": "Spares", "budget": 7572000.0},
            {"name": "Hurkus", "budget": 0.0},
            {"name": "Cost", "budget": 0.0},
            {"name": "Other", "budget": 0.0},
            {"name": "VLJ", "budget": 0.0},
            {"name": "V280", "budget": 0.0},
            {"name": "T7A", "budget": 615000.0},
            {"name": "Supernal", "budget": 0.0},
            {"name": "Superjet 100", "budget": 0.0},
            {"name": "SPECTRUM", "budget": 0.0},
            {"name": "Not Using", "budget": 0.0},
            {"name": "M345", "budget": 0.0},
            {"name": "LAV", "budget": 0.0},
            {"name": "HA480", "budget": 0.0},
            {"name": "H160M", "budget": 0.0},
            {"name": "H160", "budget": 1303000.0},
            {"name": "Global 7000", "budget": 631000.0},
            {"name": "GLG Common", "budget": 0.0},
            {"name": "G650", "budget": 17520000.0},
            {"name": "G600", "budget": 8221000.0},
            {"name": "G550", "budget": 0.0},
            {"name": "G500", "budget": 17081000.0},
            {"name": "F35", "budget": 4080000.0},
            {"name": "Eclipse", "budget": 408000.0},
            {"name": "Dassault 7X", "budget": 1495000.0},
            {"name": "B525", "budget": 0.0},
            {"name": "B505", "budget": 0.0},
            {"name": "B429", "budget": 0.0},
            {"name": "B360", "budget": 0.0},
            {"name": "ARCHER", "budget": 0.0},
            {"name": "AJT", "budget": 2574000.0},
            {"name": "A380", "budget": 0.0},
            {"name": "A350", "budget": 5387000.0},
            {"name": "A189", "budget": 0.0},
            {"name": "A149", "budget": 0.0},
            {"name": "A139", "budget": 0.0},
            {"name": "A119", "budget": 0.0},
            {"name": "A109", "budget": 0.0},
            {"name": "1032", "budget": 0.01},
            {"name": "1018", "budget": 0.01},
        ]

        # Currency data
        currencies = ["CAD", "EUR", "GBP", "USD"]

        # Dummy ItemType data (edit as needed)
        item_types = [
            {"code": "Manufactured", "description": "Manufactured"},
            {"code": "Purchased", "description": "Purchased"},
            {"code": "Subcontracted Service", "description": "Subcontracted"},
            {"code": "Cost", "description": "Cost"},
        ]

        # Dummy ItemGroup data (code + relations only)
        # Map with: code, type_code (ItemGroupType.code), program_name (Program.name)
        item_groups = [
            {'code': 'BELL02', 'type_code': 'b525', 'program_name': 'B525'},
            {'code': 'BELLZ2', 'type_code': 'b525', 'program_name': 'B525'},
            {'code': '501', 'type_code': 'cost', 'program_name': 'Cost'},
            {'code': '550', 'type_code': 'cost', 'program_name': 'Cost'},
            {'code': 'JSF001', 'type_code': 'cost', 'program_name': 'Cost'},
            {'code': '01CUST', 'type_code': 'customer_property', 'program_name': 'Not Using'},
            {'code': 'A109ZZ', 'type_code': 'customer_property', 'program_name': 'A109'},
            {'code': 'A119ZZ', 'type_code': 'customer_property', 'program_name': 'A119'},
            {'code': 'A139Z1', 'type_code': 'customer_property', 'program_name': 'A139'},
            {'code': 'A139ZZ', 'type_code': 'customer_property', 'program_name': 'A139'},
            {'code': 'A189ZZ', 'type_code': 'customer_property', 'program_name': 'A189'},
            {'code': 'A380ZZ', 'type_code': 'customer_property', 'program_name': 'A380'},
            {'code': 'AIDCZZ', 'type_code': 'customer_property', 'program_name': 'AJT'},
            {'code': 'ARC1ZZ', 'type_code': 'customer_property', 'program_name': 'ARCHER'},
            {'code': 'BELLZ1', 'type_code': 'customer_property', 'program_name': 'B429'},
            {'code': 'BELLZ3', 'type_code': 'customer_property', 'program_name': 'B505'},
            {'code': 'E500ZZ', 'type_code': 'customer_property', 'program_name': 'Eclipse'},
            {'code': 'EUR1ZZ', 'type_code': 'customer_property', 'program_name': 'H160'},
            {'code': 'GULVZ2', 'type_code': 'customer_property', 'program_name': 'A350'},
            {'code': 'GULVZ3', 'type_code': 'customer_property', 'program_name': '1032'},
            {'code': 'GULVZ4', 'type_code': 'customer_property', 'program_name': '1018'},
            {'code': 'GULVZ5', 'type_code': 'customer_property', 'program_name': 'G550'},
            {'code': 'GULVZ6', 'type_code': 'customer_property', 'program_name': 'G650'},
            {'code': 'GULVZ7', 'type_code': 'customer_property', 'program_name': 'G500'},
            {'code': 'GULVZ8', 'type_code': 'customer_property', 'program_name': 'G600'},
            {'code': 'GULVZ9', 'type_code': 'customer_property', 'program_name': 'T7A'},
            {'code': 'HANWZ1', 'type_code': 'customer_property', 'program_name': 'LAV'},
            {'code': 'HONZZ1', 'type_code': 'customer_property', 'program_name': 'HA480'},
            {'code': 'LM00ZZ', 'type_code': 'customer_property', 'program_name': 'F35'},
            {'code': 'SAFRZ2', 'type_code': 'customer_property', 'program_name': 'Superjet 100'},
            {'code': 'V280ZZ', 'type_code': 'customer_property', 'program_name': 'V280'},
            {'code': 'LM0010', 'type_code': 'f35', 'program_name': 'F35'},
            {'code': 'LM0020', 'type_code': 'f35', 'program_name': 'F35'},
            {'code': 'LM0021', 'type_code': 'f35', 'program_name': 'F35'},
            {'code': 'LM0022', 'type_code': 'f35', 'program_name': 'F35'},
            {'code': 'LM0030', 'type_code': 'f35', 'program_name': 'F35'},
            {'code': 'LM0031', 'type_code': 'f35', 'program_name': 'F35'},
            {'code': 'LM0032', 'type_code': 'f35', 'program_name': 'F35'},
            {'code': 'LM0040', 'type_code': 'f35', 'program_name': 'F35'},
            {'code': 'LM0041', 'type_code': 'f35', 'program_name': 'F35'},
            {'code': 'LM0042', 'type_code': 'f35', 'program_name': 'F35'},
            {'code': 'LM0050', 'type_code': 'f35', 'program_name': 'F35'},
            {'code': 'A10901', 'type_code': 'legacy', 'program_name': 'A109'},
            {'code': 'A10902', 'type_code': 'legacy', 'program_name': 'A109'},
            {'code': 'A10909', 'type_code': 'legacy', 'program_name': 'A109'},
            {'code': 'A38001', 'type_code': 'legacy', 'program_name': 'A380'},
            {'code': 'AIDC01', 'type_code': 'legacy', 'program_name': 'AJT'},
            {'code': 'AIDC02', 'type_code': 'legacy', 'program_name': 'AJT'},
            {'code': 'BELL01', 'type_code': 'legacy', 'program_name': 'B429'},
            {'code': 'EUR100', 'type_code': 'legacy', 'program_name': 'H160'},
            {'code': 'GLO701', 'type_code': 'legacy', 'program_name': 'Global 7000'},
            {'code': 'GLO702', 'type_code': 'legacy', 'program_name': 'Global 7000'},
            {'code': 'GULV01', 'type_code': 'legacy', 'program_name': 'G550'},
            {'code': 'GULV02', 'type_code': 'legacy', 'program_name': 'G550'},
            {'code': 'GULV09', 'type_code': 'legacy', 'program_name': 'GLG Common'},
            {'code': 'GULV10', 'type_code': 'legacy', 'program_name': 'G500'},
            {'code': 'GULV11', 'type_code': 'legacy', 'program_name': 'G500'},
            {'code': 'GULV12', 'type_code': 'legacy', 'program_name': 'G500'},
            {'code': 'GULV13', 'type_code': 'legacy', 'program_name': 'G500'},
            {'code': 'GULV14', 'type_code': 'legacy', 'program_name': 'G500'},
            {'code': 'GULV20', 'type_code': 'legacy', 'program_name': 'G650'},
            {'code': 'GULV21', 'type_code': 'legacy', 'program_name': 'G650'},
            {'code': 'GULV22', 'type_code': 'legacy', 'program_name': 'G650'},
            {'code': 'GULV23', 'type_code': 'legacy', 'program_name': 'G650'},
            {'code': 'GULV30', 'type_code': 'legacy', 'program_name': 'G600'},
            {'code': 'GULV31', 'type_code': 'legacy', 'program_name': 'G600'},
            {'code': 'GULV32', 'type_code': 'legacy', 'program_name': 'G600'},
            {'code': 'GULV40', 'type_code': 'legacy', 'program_name': '1018'},
            {'code': 'GULV41', 'type_code': 'legacy', 'program_name': '1018'},
            {'code': 'GULV42', 'type_code': 'legacy', 'program_name': '1018'},
            {'code': 'GULV50', 'type_code': 'legacy', 'program_name': 'A350'},
            {'code': 'GULV51', 'type_code': 'legacy', 'program_name': 'A350'},
            {'code': 'GULV60', 'type_code': 'legacy', 'program_name': '1032'},
            {'code': 'GULV61', 'type_code': 'legacy', 'program_name': '1032'},
            {'code': 'GULV62', 'type_code': 'legacy', 'program_name': '1032'},
            {'code': 'GULV63', 'type_code': 'legacy', 'program_name': '1032'},
            {'code': 'GULV71', 'type_code': 'legacy', 'program_name': 'GLG Common'},
            {'code': 'GULV72', 'type_code': 'legacy', 'program_name': 'GLG Common'},
            {'code': 'GULV73', 'type_code': 'legacy', 'program_name': 'GLG Common'},
            {'code': 'GULV74', 'type_code': 'legacy', 'program_name': 'GLG Common'},
            {'code': 'GULV80', 'type_code': 'legacy', 'program_name': 'T7A'},
            {'code': 'SAFR01', 'type_code': 'legacy', 'program_name': 'Dassault 7X'},
            {'code': 'SAFR02', 'type_code': 'legacy', 'program_name': 'Superjet 100'},
            {'code': 'SAFRZ1', 'type_code': 'legacy', 'program_name': 'Dassault 7X'},
            {'code': 'A10908', 'type_code': 'mro', 'program_name': 'A109'},
            {'code': 'A11901', 'type_code': 'mro', 'program_name': 'A119'},
            {'code': 'A11902', 'type_code': 'mro', 'program_name': 'A119'},
            {'code': 'A11908', 'type_code': 'mro', 'program_name': 'A119'},
            {'code': 'A13903', 'type_code': 'mro', 'program_name': 'A139'},
            {'code': 'A13908', 'type_code': 'mro', 'program_name': 'A139'},
            {'code': 'A13909', 'type_code': 'mro', 'program_name': 'A139'},
            {'code': 'A13911', 'type_code': 'mro', 'program_name': 'A139'},
            {'code': 'A139Z2', 'type_code': 'mro', 'program_name': 'A139'},
            {'code': 'A14901', 'type_code': 'mro', 'program_name': 'A149'},
            {'code': 'A18901', 'type_code': 'mro', 'program_name': 'A189'},
            {'code': 'E50018', 'type_code': 'mro', 'program_name': 'Eclipse'},
            {'code': 'GULV08', 'type_code': 'mro', 'program_name': 'G550'},
            {'code': 'GULZZ1', 'type_code': 'mro', 'program_name': 'G550'},
            {'code': 'GULZZ2', 'type_code': 'mro', 'program_name': 'G650'},
            {'code': 'GULZZ3', 'type_code': 'mro', 'program_name': 'G500'},
            {'code': 'GULZZ4', 'type_code': 'mro', 'program_name': 'G600'},
            {'code': '500', 'type_code': 'not_using', 'program_name': 'Not Using'},
            {'code': '00BUSH', 'type_code': 'not_using', 'program_name': 'Not Using'},
            {'code': '00CUST', 'type_code': 'not_using', 'program_name': 'Not Using'},
            {'code': '00FORG', 'type_code': 'not_using', 'program_name': 'Not Using'},
            {'code': '00HRDW', 'type_code': 'not_using', 'program_name': 'Not Using'},
            {'code': '00MFG2', 'type_code': 'not_using', 'program_name': 'Not Using'},
            {'code': '00MFG3', 'type_code': 'not_using', 'program_name': 'Not Using'},
            {'code': '00VALV', 'type_code': 'not_using', 'program_name': 'Not Using'},
            {'code': '01ASSY', 'type_code': 'not_using', 'program_name': 'Not Using'},
            {'code': 'BUSH01', 'type_code': 'not_using', 'program_name': 'Not Using'},
            {'code': 'DJET01', 'type_code': 'not_using', 'program_name': 'Not Using'},
            {'code': 'PIP001', 'type_code': 'not_using', 'program_name': 'Not Using'},
            {'code': 'ZZZZ01', 'type_code': 'not_using', 'program_name': 'Not Using'},
            {'code': 'ZZZZ09', 'type_code': 'not_using', 'program_name': 'Not Using'},
            {'code': 'ZZZZZZ', 'type_code': 'not_using', 'program_name': 'Not Using'},
            {'code': 'ARC001', 'type_code': 'npi', 'program_name': 'ARCHER'},
            {'code': 'BELL04', 'type_code': 'npi', 'program_name': 'B360'},
            {'code': 'BELLZ4', 'type_code': 'npi', 'program_name': 'B360'},
            {'code': 'EUR200', 'type_code': 'npi', 'program_name': 'H160M'},
            {'code': 'HON001', 'type_code': 'npi', 'program_name': 'HA480'},
            {'code': 'M34501', 'type_code': 'npi', 'program_name': 'M345'},
            {'code': 'SUP001', 'type_code': 'npi', 'program_name': 'Supernal'},
            {'code': '100', 'type_code': 'other', 'program_name': 'Other'},
            {'code': '101', 'type_code': 'other', 'program_name': 'Other'},
            {'code': '190', 'type_code': 'other', 'program_name': 'Other'},
            {'code': 'GULVZZ', 'type_code': 'other', 'program_name': 'Other'},
            {'code': 'E50001', 'type_code': 'slow_moving', 'program_name': 'Eclipse'},
            {'code': 'E50009', 'type_code': 'slow_moving', 'program_name': 'Eclipse'},
            {'code': 'HANW01', 'type_code': 'slow_moving', 'program_name': 'LAV'},
            {'code': 'HANW02', 'type_code': 'slow_moving', 'program_name': 'VLJ'},
            {'code': 'HUR002', 'type_code': 'slow_moving', 'program_name': 'Hurkus'},
            {'code': 'V28000', 'type_code': 'slow_moving', 'program_name': 'V280'},
        ]

        # Mrp Reschedule Days Classification rules
        mrp_reschedule_rules = [
            {"name": "<=7",  "min_days": None, "max_days": 7},
            {"name": "8-15", "min_days": 8, "max_days": 15},
            {"name": "16-30", "min_days": 16, "max_days": 30},
            {"name": "31-60", "min_days": 31, "max_days": 60},
            {"name": "61-90", "min_days": 61, "max_days": 90},
            {"name": "90+", "min_days": 90, "max_days": None},
        ]

        # Purchase Order Categories (top-level examples)
        po_categories = [
            {"code": "1", "description": "	Raw Material", "parent_code": None},
            {"code": "2", "description": "Purchased Parts", "parent_code": None},
            {"code": "3", "description": "Service", "parent_code": None},
            {"code": "4", "description": "4", "parent_code": None},
            {"code": "5", "description": "5", "parent_code": None},
            {"code": "6", "description": "Outside Process", "parent_code": None},
            {"code": "7", "description": "7", "parent_code": None},
            {"code": "8", "description": "8", "parent_code": None},
            {"code": "9", "description": "Charges", "parent_code": None},
        ]

        # Purchase Settings (singleton)
        purchase_settings_defaults = {"otd_target_percent": 80}

        # Global Settings (singleton)
        global_settings_defaults = {
            "fiscal_year_start_month": 10,
            "fiscal_year_start_day": 1,
            "home_currency_code": "CAD",
        }

        # Purchase Timeliness Classification rules (example buckets)
        ptc_rules = [
            {
                "name": "Early",
                "priority": 0,
                "active": True,
                "counts_for_ontime": True,
                "min_days": -9999999,
                "min_inclusive": True,
                "max_days": 0,
                "max_inclusive": False,
                "color": "#2196F3",
                "description": "-",
            },
            {
                "name": "On Time",
                "priority": 0,
                "active": True,
                "counts_for_ontime": True,
                "min_days": 0,
                "min_inclusive": True,
                "max_days": 10,
                "max_inclusive": False,
                "color": "	#2E7D32",
                "description": "-",
            },
            {
                "name": "Late",
                "priority": 0,
                "active": True,
                "counts_for_ontime": False,
                "min_days": 10,
                "min_inclusive": True,
                "max_days": 30,
                "max_inclusive": False,
                "color": "#F9A825",
                "description": "-",
            },
            {
                "name": "Very Late",
                "priority": 0,
                "active": True,
                "counts_for_ontime": False,
                "min_days": 30,
                "min_inclusive": True,
                "max_days": None,
                "max_inclusive": True,
                "color": "#C62828",
                "description": "-",
            },
        ]

        # Units of Measure
        uoms = [
            {"code": "EA", "name": "Each"},
            {"code": "IN", "name": "Inches"},
        ]

        created_counts = {
            "item_group_types": 0,
            "programs": 0,
            "currencies": 0,
            "item_types": 0,
            "item_groups": 0,
            "mrp_reschedule_rules": 0,
            "po_categories": 0,
            "purchase_settings": 0,
            "global_settings": 0,
            "ptc_rules": 0,
            "uoms": 0,
        }

        # Create ItemGroupType entries
        for data in item_group_types:
            obj, created = ItemGroupType.objects.get_or_create(
                code=data["code"], defaults={"description": data["description"]}
            )
            if created:
                created_counts["item_group_types"] += 1
                self.stdout.write(self.style.SUCCESS(f"Created ItemGroupType: {obj.code}"))
            else:
                # Update description if changed to keep data tidy on re-runs
                if obj.description != data["description"]:
                    obj.description = data["description"]
                    obj.save(update_fields=["description"])
                self.stdout.write(self.style.WARNING(f"ItemGroupType exists: {obj.code}"))

        # Helper to generate canonical codes from names
        def code_from_name(name: str) -> str:
            if not name:
                return "UNKNOWN"
            return " ".join(name.strip().split()).lower().replace(" ", "_")

        # Create Program entries (use code for identity; keep name in sync)
        for data in programs:
            code = code_from_name(data["name"]) if not data.get("code") else data["code"]
            obj, created = Program.objects.get_or_create(
                code=code, defaults={"name": data["name"], "budget": data["budget"]}
            )
            if created:
                created_counts["programs"] += 1
                self.stdout.write(self.style.SUCCESS(f"Created Program: {obj.name}"))
            else:
                # Update budget/name if changed to keep data tidy on re-runs
                changed = False
                if obj.budget != data["budget"]:
                    obj.budget = data["budget"]
                    changed = True
                if obj.name != data["name"]:
                    obj.name = data["name"]
                    changed = True
                if changed:
                    obj.save(update_fields=["budget", "name"])
                self.stdout.write(self.style.WARNING(f"Program exists: {obj.name}"))

        # Create Currency entries
        for code in currencies:
            obj, created = Currency.objects.get_or_create(code=code)
            if created:
                created_counts["currencies"] += 1
                self.stdout.write(self.style.SUCCESS(f"Created Currency: {obj.code}"))
            else:
                self.stdout.write(self.style.WARNING(f"Currency exists: {obj.code}"))

        # Create ItemType entries
        for data in item_types:
            obj, created = ItemType.objects.get_or_create(
                code=data["code"], defaults={"description": data["description"]}
            )
            if created:
                created_counts["item_types"] += 1
                self.stdout.write(self.style.SUCCESS(f"Created ItemType: {obj.code}"))
            else:
                if obj.description != data["description"]:
                    obj.description = data["description"]
                    obj.save(update_fields=["description"])
                self.stdout.write(self.style.WARNING(f"ItemType exists: {obj.code}"))

        # Create/Update MRP Reschedule Days Classification
        for data in mrp_reschedule_rules:
            obj, created = MrpRescheduleDaysClassification.objects.get_or_create(
                name=data["name"], defaults={"min_days": data["min_days"], "max_days": data["max_days"]}
            )
            if created:
                created_counts["mrp_reschedule_rules"] += 1
                self.stdout.write(self.style.SUCCESS(f"Created MRP Reschedule Rule: {obj.name}"))
            else:
                changed = False
                if obj.min_days != data["min_days"]:
                    obj.min_days = data["min_days"]
                    changed = True
                if obj.max_days != data["max_days"]:
                    obj.max_days = data["max_days"]
                    changed = True
                if changed:
                    obj.save(update_fields=["min_days", "max_days"])
                self.stdout.write(self.style.WARNING(f"MRP Rule exists: {obj.name}"))

        # Create/Update Purchase Order Categories (flat)
        for data in po_categories:
            parent = None
            if data.get("parent_code"):
                parent = PurchaseOrderCategory.objects.filter(code=data["parent_code"]).first()
            obj, created = PurchaseOrderCategory.objects.get_or_create(
                code=data["code"], parent=parent, defaults={"description": data.get("description", "")}
            )
            if created:
                created_counts["po_categories"] += 1
                self.stdout.write(self.style.SUCCESS(f"Created PO Category: {obj.code}"))
            else:
                if data.get("description") is not None and obj.description != data["description"]:
                    obj.description = data["description"]
                    obj.save(update_fields=["description"])
                self.stdout.write(self.style.WARNING(f"PO Category exists: {obj.code}"))

        # Ensure a single PurchaseSettings row exists (pk=1 convention)
        ps_obj, ps_created = PurchaseSettings.objects.get_or_create(pk=1, defaults=purchase_settings_defaults)
        if ps_created:
            created_counts["purchase_settings"] += 1
            self.stdout.write(self.style.SUCCESS("Created PurchaseSettings (pk=1)"))
        else:
            # Update OTD target if changed
            if ps_obj.otd_target_percent != purchase_settings_defaults["otd_target_percent"]:
                ps_obj.otd_target_percent = purchase_settings_defaults["otd_target_percent"]
                ps_obj.save(update_fields=["otd_target_percent"])
            self.stdout.write(self.style.WARNING("PurchaseSettings exists (pk=1)"))

        # Ensure a single GlobalSettings row exists (pk=1 convention)
        gs_obj, gs_created = GlobalSettings.objects.get_or_create(pk=1, defaults=global_settings_defaults)
        if gs_created:
            created_counts["global_settings"] += 1
            self.stdout.write(self.style.SUCCESS("Created GlobalSettings (pk=1)"))
        else:
            changed = False
            if gs_obj.fiscal_year_start_month != global_settings_defaults["fiscal_year_start_month"]:
                gs_obj.fiscal_year_start_month = global_settings_defaults["fiscal_year_start_month"]
                changed = True
            if gs_obj.fiscal_year_start_day != global_settings_defaults["fiscal_year_start_day"]:
                gs_obj.fiscal_year_start_day = global_settings_defaults["fiscal_year_start_day"]
                changed = True
            if gs_obj.home_currency_code != global_settings_defaults["home_currency_code"]:
                gs_obj.home_currency_code = global_settings_defaults["home_currency_code"]
                changed = True
            if changed:
                gs_obj.save(update_fields=["fiscal_year_start_month", "fiscal_year_start_day", "home_currency_code"])
            self.stdout.write(self.style.WARNING("GlobalSettings exists (pk=1)"))

        # Create/Update Purchase Timeliness Classification rules
        for data in ptc_rules:
            obj, created = PurchaseTimelinessClassification.objects.get_or_create(
                name=data["name"], defaults={
                    "priority": data["priority"],
                    "active": data["active"],
                    "counts_for_ontime": data["counts_for_ontime"],
                    "min_days": data["min_days"],
                    "min_inclusive": data["min_inclusive"],
                    "max_days": data["max_days"],
                    "max_inclusive": data["max_inclusive"],
                    "color": data.get("color", ""),
                    "description": data.get("description", ""),
                }
            )
            if created:
                created_counts["ptc_rules"] += 1
                self.stdout.write(self.style.SUCCESS(f"Created PTC Rule: {obj.name}"))
            else:
                changed = False
                for field in [
                    "priority", "active", "counts_for_ontime", "min_days", "min_inclusive", "max_days", "max_inclusive", "color", "description"
                ]:
                    new_val = data.get(field)
                    if getattr(obj, field) != new_val:
                        setattr(obj, field, new_val)
                        changed = True
                if changed:
                    obj.save(update_fields=[
                        "priority", "active", "counts_for_ontime", "min_days", "min_inclusive", "max_days", "max_inclusive", "color", "description"
                    ])
                self.stdout.write(self.style.WARNING(f"PTC Rule exists: {obj.name}"))

        # Create/Update UOMs
        for data in uoms:
            obj, created = UOM.objects.get_or_create(code=data["code"], defaults={"name": data["name"]})
            if created:
                created_counts["uoms"] += 1
                self.stdout.write(self.style.SUCCESS(f"Created UOM: {obj.code}"))
            else:
                if obj.name != data["name"]:
                    obj.name = data["name"]
                    obj.save(update_fields=["name"])
                self.stdout.write(self.style.WARNING(f"UOM exists: {obj.code}"))

        # Create ItemGroup entries (code, type, program only; leave description empty)
        for data in item_groups:
            ig_type, _ = ItemGroupType.objects.get_or_create(code=data["type_code"], defaults={"description": ""})
            prog_code = code_from_name(data.get("program_name", "")) if data.get("program_name") else None
            program = None
            if prog_code:
                program, _ = Program.objects.get_or_create(
                    code=prog_code, defaults={"name": data.get("program_name", prog_code), "budget": 0.0}
                )

            obj, created = ItemGroup.objects.get_or_create(
                code=data["code"], defaults={"type": ig_type, "program": program}
            )
            if created:
                created_counts["item_groups"] += 1
                self.stdout.write(self.style.SUCCESS(f"Created ItemGroup: {obj.code}"))
            else:
                changed = False
                if obj.type_id != ig_type.id:
                    obj.type = ig_type
                    changed = True
                if obj.program_id != program.id:
                    obj.program = program
                    changed = True
                if changed:
                    obj.save(update_fields=["type", "program"])
                self.stdout.write(self.style.WARNING(f"ItemGroup exists: {obj.code}"))

        self.stdout.write(
            self.style.SUCCESS(
                "Seeding completed: "
                f"ItemGroupTypes created={created_counts['item_group_types']}, "
                f"Programs created={created_counts['programs']}, "
                f"Currencies created={created_counts['currencies']}, "
                f"ItemTypes created={created_counts['item_types']}, "
                f"ItemGroups created={created_counts['item_groups']}, "
                f"MRP rules created={created_counts['mrp_reschedule_rules']}, "
                f"PO categories created={created_counts['po_categories']}, "
                f"PurchaseSettings created={created_counts['purchase_settings']}, "
                f"GlobalSettings created={created_counts['global_settings']}, "
                f"PTC rules created={created_counts['ptc_rules']}, "
                f"UOMs created={created_counts['uoms']}"
            )
        )
