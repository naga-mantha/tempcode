# django_bi/workflow/views/transition.py

from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404, redirect
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from django.http import HttpResponseForbidden
from django_bi.workflow.apply_transition import apply_transition

@require_POST
def perform_transition(request, app_label, model_name, object_id, transition_name):
    model = ContentType.objects.get(app_label=app_label, model=model_name).model_class()
    obj = get_object_or_404(model, pk=object_id)

    try:
        apply_transition(obj, transition_name, request.user)
        messages.success(request, f"Transition '{transition_name}' successful.")
    except Exception as e:
        messages.error(request, str(e))
        return HttpResponseForbidden()

    return redirect(request.META.get("HTTP_REFERER", "/"))
