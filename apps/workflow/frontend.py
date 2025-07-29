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
            "url": f"/workflow/transition/{obj._meta.app_label}/{obj._meta.model_name}/{obj.pk}/{t.name}/",  # generic handler
        })

    return buttons
