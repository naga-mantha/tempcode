from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
import inspect

from apps.blocks.registry import block_registry


class FilterChoicesView(LoginRequiredMixin, View):
    """Return choices for a filter field via AJAX."""

    def get(self, request, block_name, key):
        block_impl = block_registry.get(block_name)
        if not block_impl:
            return JsonResponse([], safe=False)

        raw_schema = block_impl.get_filter_schema(request)
        cfg = raw_schema.get(key, {})
        choices_callable = cfg.get("choices")
        query = request.GET.get("q", "")
        ids_param = request.GET.get("ids", "")
        results = []
        choices = []

        # Parse preselected values (for label hydration in AJAX selects)
        raw_tokens: list[str] = []
        if ids_param:
            try:
                raw_tokens = [x.strip() for x in ids_param.split(",") if x.strip()]
            except Exception:
                raw_tokens = []

        if callable(choices_callable):
            try:
                sig = inspect.signature(choices_callable)
                params = sig.parameters
                kwargs = {}
                args = [request.user]
                if "query" in params:
                    kwargs["query"] = query
                elif len(params) >= 2:
                    args.append(query)
                if "ids" in params:
                    kwargs["ids"] = raw_tokens
                choices = choices_callable(*args, **kwargs)
            except Exception:
                choices = []
        elif isinstance(cfg.get("choices"), (list, tuple)):
            choices = cfg.get("choices")

        q_lower = query.lower()
        for value, label in choices:
            label_str = str(label)
            if not query or q_lower in label_str.lower():
                results.append({"value": value, "label": label_str})
        return JsonResponse(results, safe=False)
