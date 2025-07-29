from django.core.exceptions import PermissionDenied
from .models import Transition, TransitionLog
from django.contrib.contenttypes.models import ContentType

def get_allowed_transitions(obj, user):
    state = getattr(obj, "workflow_state", None)
    workflow = getattr(obj, "workflow", None)

    if not state or not workflow:
        return []

    transitions = Transition.objects.filter(
        workflow=workflow,
        source_state=state
    ).prefetch_related("allowed_groups")

    return [
        t for t in transitions
        if user.groups.filter(id__in=t.allowed_groups.values_list("id", flat=True)).exists()
    ]

def apply_transition(obj, transition_name, user, *, comment="", save=True):
    allowed_transitions = get_allowed_transitions(obj, user)

    transition = next((t for t in allowed_transitions if t.name == transition_name), None)
    if not transition:
        raise PermissionDenied(f"User is not allowed to perform transition '{transition_name}'.")

    from_state = obj.workflow_state
    obj.workflow_state = transition.dest_state
    if save:
        obj.save(update_fields=["workflow_state"])

    # Create log
    TransitionLog.objects.create(
        user=user,
        content_type=ContentType.objects.get_for_model(obj),
        object_id=obj.pk,
        from_state=from_state,
        to_state=transition.dest_state,
        transition=transition,
        comment=comment
    )

    return transition.dest_state
