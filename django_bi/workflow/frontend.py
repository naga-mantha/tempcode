from django.urls import reverse

from .apply_transition import get_allowed_transitions

def render_transition_buttons(obj, user):
    transitions = get_allowed_transitions(obj, user)
    buttons = []

    for t in transitions:
        buttons.append({
            "label": t.name,
            "transition_name": t.name,
            "from_state": t.source_state.name,
            "to_state": t.dest_state.name,
            "url": reverse(
                "workflow:workflow_perform_transition",
                kwargs={
                    "app_label": obj._meta.app_label,
                    "model_name": obj._meta.model_name,
                    "object_id": obj.pk,
                    "transition_name": t.name,
                },
            ),
        })

    return buttons
