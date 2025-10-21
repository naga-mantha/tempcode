from django.core.management.base import BaseCommand
from django.apps import apps as django_apps

from apps.django_bi.blocks.models.field_display_rule import FieldDisplayRule


TARGET_MODELS = [
    "common.Item",
    "common.BusinessPartner",
    "common.PurchaseOrder",
    "common.PurchaseOrderLine",
    "common.Receipt",
    "common.ReceiptLine",
    "common.PlannedPurchaseOrder",
    "common.PurchaseMrpMessage",
    "common.ItemGroupType",
    "common.Program",
    "common.ItemGroup",
    "common.ItemType",
]


class Command(BaseCommand):
    help = (
        "Create FieldDisplayRule exclusions for workflow-related fields on the given models.\n"
        "For each target model, if fields exist, marks 'workflow', 'workflow_state' (and their *_id) as excluded.\n"
        "Skips fields that are not present on a model."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Show what would be created/updated without writing to the database.",
        )
        parser.add_argument(
            "--models",
            nargs="*",
            default=None,
            help=(
                "Optional space-separated list of model labels to limit the operation. "
                "Defaults to the built-in list if not provided."
            ),
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))
        selected = options.get("models") or TARGET_MODELS
        created = 0
        updated = 0
        skipped_models = []

        # Fields to consider excluding. We include the *_id variants in case
        # any views surface the raw FK column name.
        candidate_fields = ("workflow", "workflow_state", "workflow_id", "workflow_state_id")

        for label in selected:
            try:
                model = django_apps.get_model(label)
            except (LookupError, ValueError):
                self.stdout.write(self.style.WARNING(f"Model not found: {label}; skipping."))
                continue

            model_fields = {f.name for f in getattr(model, "_meta").fields}
            # Only act on fields that actually exist on the model
            target_fields = [f for f in candidate_fields if f in model_fields]
            if not target_fields:
                skipped_models.append(label)
                continue

            for field_name in target_fields:
                if dry_run:
                    self.stdout.write(
                        f"[DRY-RUN] Would set is_excluded=True for {label}.{field_name}"
                    )
                    continue
                obj, created_flag = FieldDisplayRule.objects.update_or_create(
                    model_label=label,
                    field_name=field_name,
                    defaults={"is_excluded": True, "is_mandatory": False},
                )
                if created_flag:
                    created += 1
                else:
                    # If it already existed, ensure flags are correct
                    # update_or_create already applied defaults, but mark as updated for reporting
                    updated += 1

        if dry_run:
            self.stdout.write(self.style.SUCCESS("Dry run complete."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Done. Created: {created}, Updated: {updated}"))

        if skipped_models:
            self.stdout.write(
                self.style.NOTICE(
                    "Models without workflow fields (skipped): " + ", ".join(skipped_models)
                )
            )

