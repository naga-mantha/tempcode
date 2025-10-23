from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils.text import capfirst, slugify

from apps.django_bi.workflow.models import Workflow


def _is_workflow_enabled_model(model) -> bool:
    try:
        model._meta.get_field("workflow")
        model._meta.get_field("workflow_state")
        return True
    except Exception:
        return False


def generate_workflow_permissions_for_model(model):
    """Ensure per-state instance and field permissions exist for ``model``.

    Returns (created_count, deleted_count).
    Skips abstract or proxy models and models without workflow fields.
    """

    opts = model._meta
    if opts.proxy or opts.abstract:
        return 0, 0
    if not _is_workflow_enabled_model(model):
        return 0, 0

    ct = ContentType.objects.get_for_model(model, for_concrete_model=False)
    model_name = opts.model_name
    verbose_name = capfirst(opts.verbose_name)

    # Gather workflows and state codes
    workflows = Workflow.objects.filter(content_type=ct)
    state_codes = []
    for wf in workflows:
        for state in wf.states.all():
            state_codes.append((state, slugify(state.name)))

    # Collect editable fields (including M2M)
    fields = [
        f for f in list(opts.fields) + list(opts.many_to_many) if not f.auto_created and f.editable
    ]

    expected = {}
    for state, code in state_codes:
        # Instance-level perms
        expected[f"view_{model_name}_{code}"] = f'Can view "{verbose_name}" in state "{state.name}"'
        expected[f"change_{model_name}_{code}"] = f'Can change "{verbose_name}" in state "{state.name}"'
        expected[f"delete_{model_name}_{code}"] = f'Can delete "{verbose_name}" in state "{state.name}"'
        # Field-level perms
        for field in fields:
            fname = field.name
            expected[f"view_{model_name}_{fname}_{code}"] = (
                f'Can view field "{fname}" on "{verbose_name}" in state "{state.name}"'
            )
            expected[f"change_{model_name}_{fname}_{code}"] = (
                f'Can change field "{fname}" on "{verbose_name}" in state "{state.name}"'
            )

    # Existing codenames for this content type that look like state perms
    existing_all = set(Permission.objects.filter(content_type=ct).values_list("codename", flat=True))
    # Detect codenames ending with any state suffix to avoid touching non-state perms
    state_suffixes = {f"_{code}" for (_s, code) in state_codes}
    existing_state_like = {
        c for c in existing_all if any(c.endswith(suf) for suf in state_suffixes)
    }

    to_delete = existing_state_like - expected.keys()
    deleted_count = 0
    if to_delete:
        deleted_count, _ = Permission.objects.filter(content_type=ct, codename__in=to_delete).delete()

    # Create missing
    existing_now = set(Permission.objects.filter(content_type=ct).values_list("codename", flat=True))
    to_create = [
        Permission(codename=codename, name=name, content_type=ct)
        for codename, name in expected.items()
        if codename not in existing_now
    ]
    created_objs = Permission.objects.bulk_create(to_create)
    created_count = len(created_objs)

    return created_count, deleted_count

