from apps.django_bi.blocks.models.block_column_config import BlockColumnConfig
from apps.django_bi.permissions.checks import can_read_field
from apps.django_bi.workflow.permissions import can_read_field_state  # noqa: F401 (reserved for future use)
from django.db import models
from .field_rules import get_field_display_rules

def get_user_column_config(user, block):
    # Prefer user's private default; else a public default; else first private; else first public
    qs = BlockColumnConfig.objects.filter(block=block)
    config = (
        qs.filter(user=user, is_default=True).first()
        or qs.filter(visibility=BlockColumnConfig.VISIBILITY_PUBLIC, is_default=True).first()
        or qs.filter(user=user).first()
        or qs.filter(visibility=BlockColumnConfig.VISIBILITY_PUBLIC).first()
    )
    return config.fields if config else []

def get_model_fields_for_column_config(model, user, *, max_depth=10):
    """
    Return field metadata for `model`, expanding ForeignKey chains up to `max_depth`.

    - Respects field display rules and user read permissions at each level.
    - Skips related primary key (`id`) fields.
    - Marks only top-level, non-FK fields as editable.
    - Prevents cycles by not revisiting models in the current traversal path.
    """

    def rules_for(m):
        lbl = f"{m._meta.app_label}.{m.__name__}"
        r = get_field_display_rules(model_label=lbl)
        return {x.field_name: x for x in r}

    fields = []

    def walk(current_model, prefix="", depth=0, path=None):
        nonlocal fields
        path = tuple(path or ())
        rule_map = rules_for(current_model)
        for f in current_model._meta.fields:
            # Hide fields excluded by display rules
            rule = rule_map.get(f.name)
            if rule and rule.is_excluded:
                continue

            # Permission check (allow mandatory fields regardless)
            if user and not can_read_field(user, current_model, f.name):
                if not (rule and rule.is_mandatory):
                    continue

            if isinstance(f, models.ForeignKey):
                # Do not add the FK itself; expand into related model fields
                if depth >= max_depth:
                    continue
                rel_model = f.remote_field.model
                # Prevent infinite loops on cyclic relationships
                if rel_model in path:
                    continue
                walk(rel_model, prefix=f"{prefix}{f.name}__", depth=depth + 1, path=path + (current_model,))
                continue

            # For related models (prefix non-empty), skip their primary key
            if prefix and f.name == "id":
                continue

            fields.append(
                {
                    "name": f"{prefix}{f.name}",
                    "label": f.verbose_name,
                    "model": f"{current_model._meta.label}",
                    "mandatory": rule.is_mandatory if rule else False,
                    "editable": (depth == 0),
                }
            )

        # Also expand reverse OneToOne relations (e.g., PurchaseOrderLine -> MrpMessage)
        # Treat them like forward FKs for traversal purposes
        for rel in getattr(current_model._meta, "related_objects", []):
            try:
                is_o2o = isinstance(rel, models.OneToOneRel)
            except Exception:
                is_o2o = False
            if not is_o2o:
                continue
            if depth >= max_depth:
                continue
            rel_model = rel.related_model
            if rel_model in path:
                continue
            accessor = rel.get_accessor_name() or rel.name
            # Walk into the related model using the reverse accessor name
            walk(rel_model, prefix=f"{prefix}{accessor}__", depth=depth + 1, path=path + (current_model,))

    walk(model, prefix="", depth=0, path=(model,))
    return fields

