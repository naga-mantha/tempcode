import json
from pathlib import Path

from django.apps import apps as django_apps
from django.core.management.base import BaseCommand, CommandError

from apps.blocks.models.field_display_rule import FieldDisplayRule


# Default mapping embedded in the script. Adjust as needed.
# Keys are Django model labels ("app_label.ModelName").
# Values are lists of field names to set is_excluded=True for.
# Note: For ForeignKey fields like "workflow" and "workflow_state",
# excluding them at the top-level prevents traversal into related fields
# in Manage Columns. The raw "*_id" DB columns are not separate model
# fields and are therefore not necessary to list here.
DEFAULT_CONFIG: dict[str, list[str]] = {
    "blocks.Item": ["item_group", "type"],
    "blocks.ItemGroup": [],
    "blocks.ItemType": [],
}


class Command(BaseCommand):
    help = (
        "Set FieldDisplayRule.is_excluded=True for specified model fields.\n\n"
        "Provide a JSON mapping of model labels to field lists, e.g.:\n"
        "  {\n"
        "    \"blocks.Item\": [\"item_group\", \"type\"]\n"
        "  }\n\n"
        "Fields that do not exist on the model are reported and skipped."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--config",
            dest="config",
            help="Inline JSON mapping of model_label -> [fields...]",
        )
        parser.add_argument(
            "--config-file",
            dest="config_file",
            help="Path to a JSON file containing the mapping of model_label -> [fields...]",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Preview changes without writing to the database.",
        )

    def _load_config(self, inline: str | None, file_path: str | None) -> dict:
        # If neither --config nor --config-file is provided, fall back to DEFAULT_CONFIG
        if not inline and not file_path:
            return DEFAULT_CONFIG
        if file_path:
            p = Path(file_path)
            if not p.exists():
                raise CommandError(f"Config file not found: {file_path}")
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                raise CommandError(f"Invalid JSON in {file_path}: {e}")
        try:
            return json.loads(inline)
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON for --config: {e}")

    def handle(self, *args, **options):
        cfg = self._load_config(options.get("config"), options.get("config_file"))
        dry = bool(options.get("dry_run"))

        if not isinstance(cfg, dict):
            raise CommandError("Config must be a JSON object mapping model labels to field arrays.")

        total_created = 0
        total_updated = 0

        for model_label, fields in cfg.items():
            if not isinstance(fields, (list, tuple)):
                self.stdout.write(self.style.WARNING(f"Skipping {model_label}: fields must be a list."))
                continue
            try:
                model = django_apps.get_model(model_label)
            except Exception:
                self.stdout.write(self.style.WARNING(f"Model not found: {model_label}; skipping."))
                continue

            existing_field_names = {f.name for f in getattr(model, "_meta").fields}
            for field_name in fields:
                if field_name not in existing_field_names:
                    self.stdout.write(
                        self.style.WARNING(f"{model_label}.{field_name} does not exist; skipped.")
                    )
                    continue
                if dry:
                    self.stdout.write(f"[DRY-RUN] Would set is_excluded=True for {model_label}.{field_name}")
                    continue
                obj, created = FieldDisplayRule.objects.update_or_create(
                    model_label=model_label,
                    field_name=field_name,
                    defaults={"is_excluded": True},
                )
                if created:
                    total_created += 1
                else:
                    total_updated += 1

        if dry:
            self.stdout.write(self.style.SUCCESS("Dry run complete."))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Done. Created: {total_created}, Updated: {total_updated}"
                )
            )

