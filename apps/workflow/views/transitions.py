# NOT NEEDED ANYMORE



from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from apps.workflow.models import Transition

@login_required
def apply_transition(request, app_label, model_name, pk, redirect_url_name):
    """
    Generic view: apply a Transition to any model instance via ContentType.
    Expects POST with 'transition_id'.
    """

    if request.method != "POST":
        return redirect(request.META.get("HTTP_REFERER", "/"))

    # 1. Lookup the instance by ContentType
    ct = get_object_or_404(ContentType, app_label=app_label, model=model_name)
    model = ct.model_class()
    obj = get_object_or_404(model, pk=pk)

    # 2. Lookup the transition and apply it
    t = get_object_or_404(Transition, pk=request.POST["transition_id"])
    obj.do_transition(t, request.user, comment=request.POST.get("comment", ""))

    return redirect(redirect_url_name, pk=pk)
