from django.core.exceptions import PermissionDenied
from django.contrib.contenttypes.models import ContentType
from django_bi.conf import settings

from .models import Transition, TransitionLog, Workflow

def _bypass_all(user) -> bool:
    if getattr(user, "is_superuser", False):
        return True
    staff_bypass = getattr(settings, "PERMISSIONS_STAFF_BYPASS", True)
    return staff_bypass and getattr(user, "is_staff", False)


def get_allowed_transitions(obj, user):
    state = getattr(obj, "workflow_state", None)
    workflow = getattr(obj, "workflow", None)

    if not state or not workflow:
        return []

    if workflow.status == Workflow.INACTIVE:
        return Transition.objects.none()

    transitions = Transition.objects.filter(
        workflow=workflow,
        source_state=state,
    ).prefetch_related("allowed_groups")

    if _bypass_all(user):
        return list(transitions)

    return [t for t in transitions if t.is_allowed_for_user(user)]

def apply_transition(obj, transition_name, user, *, comment="", save=True):
    allowed_transitions = get_allowed_transitions(obj, user)
    workflow = getattr(obj, "workflow", None)

    if not workflow or workflow.status == Workflow.INACTIVE:
        raise PermissionDenied("This workflow is inactive and cannot be modified.")

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
