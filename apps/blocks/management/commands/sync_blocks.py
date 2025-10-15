from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.blocks.models.block import Block
from apps.blocks.registry import get_registry
from apps.blocks.register import load_specs


class Command(BaseCommand):
    help = "Sync V2 BlockSpec registry into Block rows (DB-wins for display fields)."

    def handle(self, *args, **options):
        # Load V2 specs (registers into registry)
        load_specs()
        registry = get_registry()

        created = 0
        updated = 0

        for code, spec in registry.items():
            obj, was_created = Block.objects.get_or_create(code=code)
            if was_created:
                created += 1
                # On create, seed with spec defaults
                obj.name = spec.name
                obj.description = spec.description
                obj.category = spec.category or ""
                obj.enabled = True
                obj.override_display = True
                obj.save()
                self.stdout.write(self.style.SUCCESS(f"Created Block: {code}"))
            else:
                # DB-wins: only update display fields if override_display is False
                if not obj.override_display:
                    obj.name = spec.name
                    obj.description = spec.description
                    obj.category = spec.category or ""
                    obj.save(update_fields=["name", "description", "category"])
                    updated += 1
                    self.stdout.write(self.style.WARNING(f"Updated display for Block: {code}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Sync complete: {created} created, {updated} updated, {len(registry)} total registry entries."
            )
        )

