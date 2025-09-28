from __future__ import annotations

from typing import Iterable, Tuple

from django.core.management.base import BaseCommand, CommandParser

from apps.blocks.models.table_config import BlockTableConfig
from apps_v2.blocks.register import load_specs
from apps_v2.blocks.registry import get_registry
from apps_v2.blocks.configs import get_block_for_spec
from apps_v2.blocks.services.field_catalog import build_field_catalog
from apps_v2.policy.service import PolicyService


class Command(BaseCommand):
    help = (
        "Sync V2 table configs (columns) with current FieldDisplay rules: "
        "drop newly-excluded fields, inject newly-mandatory fields."
    )

    def add_arguments(self, parser: CommandParser) -> None:  # noqa: D401
        parser.add_argument(
            "--spec-id",
            action="append",
            dest="spec_ids",
            help="V2 spec id to sync (e.g., v2.items.table). Can be specified multiple times.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            dest="apply",
            help="Apply changes to the database (defaults to dry-run).",
        )

    def handle(self, *args, **options):  # noqa: D401
        load_specs()
        reg = get_registry()

        spec_ids = options.get("spec_ids") or []
        do_apply = bool(options.get("apply"))

        targets: Iterable[Tuple[str, object]]
        if spec_ids:
            targets = []
            for sid in spec_ids:
                spec = reg.get(sid)
                if not spec:
                    self.stdout.write(self.style.WARNING(f"Skipping unknown spec_id: {sid}"))
                    continue
                targets.append((sid, spec))
        else:
            # Discover all specs that have BlockTableConfig rows
            seen = set()
            targets = []
            for cfg in BlockTableConfig.objects.select_related("block").all():
                sid = getattr(cfg.block, "code", None)
                if not sid or sid in seen:
                    continue
                seen.add(sid)
                spec = reg.get(sid)
                if not spec:
                    self.stdout.write(self.style.WARNING(f"Skipping block without registered spec: {sid}"))
                    continue
                targets.append((sid, spec))

        total = 0
        changed = 0

        for spec_id, spec in targets:
            block = get_block_for_spec(spec_id)
            depth = int(getattr(spec, "column_max_depth", 0) or 0)
            policy = PolicyService()

            # Process each config for this block
            qs = BlockTableConfig.objects.filter(block=block).select_related("user")
            for cfg in qs:
                total += 1
                user = getattr(cfg, "user", None)
                # Build catalog with the config's user for policy-consistent allowlist
                model = getattr(spec, "model", None)
                if model is None:
                    self.stdout.write(self.style.WARNING(f"Spec {spec_id} has no model; skipping config {cfg.pk}"))
                    continue
                catalog = build_field_catalog(
                    model,
                    user=user,
                    policy=policy,
                    max_depth=depth,
                )
                allowed = [c.get("key") for c in catalog]
                allowed_set = set(allowed)
                mandatory = [c.get("key") for c in catalog if c.get("mandatory")]

                before = list(cfg.columns or [])
                after = [k for k in before if k in allowed_set]
                # Append any missing mandatory keys
                for mk in mandatory:
                    if mk not in after:
                        after.append(mk)

                if after != before:
                    changed += 1
                    self.stdout.write(
                        f"[{spec_id}] Config {cfg.pk} ({cfg.user_id}, {cfg.name}):\n"
                        f"  - before: {before}\n  - after:  {after}"
                    )
                    if do_apply:
                        cfg.columns = after
                        cfg.save(update_fields=["columns"])

        if do_apply:
            self.stdout.write(self.style.SUCCESS(f"Updated {changed} of {total} configs."))
        else:
            self.stdout.write(f"Dry-run: {changed} of {total} configs would change. Use --apply to write.")

