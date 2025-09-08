import json
from django.db import transaction
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.common.models import ToDo


def todo_list(request):
    todos = ToDo.objects.prefetch_related('dependencies').all()
    # Ordered by model Meta ordering
    context = {
        'todos': todos,
    }
    return render(request, 'todo_list.html', context)


@require_POST
def todo_reorder(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        order = data.get('order', [])
        if not isinstance(order, list):
            return HttpResponseBadRequest('Invalid payload')
    except Exception:
        return HttpResponseBadRequest('Invalid JSON')

    # Update priorities in a transaction
    with transaction.atomic():
        for idx, pk in enumerate(order):
            ToDo.objects.filter(pk=pk).update(priority=idx)

    return JsonResponse({'status': 'ok'})

