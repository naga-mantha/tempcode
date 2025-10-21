import json
from django import forms
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import FieldDoesNotExist, ValidationError

from apps.django_bi.workflow.permissions import can_write_field_state
from apps.django_bi.blocks.registry import block_registry


class InlineEditForm(forms.Form):
    id = forms.IntegerField()
    field = forms.CharField()
    value = forms.CharField(required=False)


@method_decorator(csrf_exempt, name="dispatch")
class InlineEditView(LoginRequiredMixin, View):
    form_class = InlineEditForm

    def post(self, request, block_name):
        try:
            data = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

        form = self.form_class(data)
        if not form.is_valid():
            return JsonResponse({"success": False, "error": form.errors}, status=400)

        obj_id = form.cleaned_data["id"]
        field_name = form.cleaned_data["field"]
        value = form.cleaned_data["value"]

        block = block_registry.get(block_name)
        if not block:
            return JsonResponse({"success": False, "error": "Invalid block"})

        model = block.get_model()
        instance = model.objects.get(id=obj_id)

        if not can_write_field_state(request.user, model, field_name, instance):
            return JsonResponse({"success": False, "error": "Permission denied"})

        try:
            model_field = model._meta.get_field(field_name)
            python_value = model_field.clean(value, instance)
            setattr(instance, field_name, python_value)
            instance.full_clean(validate_unique=False)
            instance.save()
        except FieldDoesNotExist:
            return JsonResponse({"success": False, "error": "Invalid field"}, status=400)
        except ValidationError as e:
            return JsonResponse({"success": False, "error": e.messages}, status=400)

        return JsonResponse({"success": True})
