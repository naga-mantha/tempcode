from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
import inspect
from typing import Optional, Iterable, Set

from apps.django_bi.blocks.registry import block_registry
from apps.django_bi.blocks.services.blocks_filter_utils import FilterResolutionMixin


class FilterChoicesView(LoginRequiredMixin, View):
    """Return choices for a filter field via AJAX with interdependent narrowing."""

    MAX_OPTIONS = 200

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

        # Resolve schema and collect current filter values (namespaced as filters.<key>)
        schema = FilterResolutionMixin._resolve_filter_schema(raw_schema, request.user)
        current_filters = FilterResolutionMixin._collect_filters(
            request.GET, schema, base={}, prefix="filters.", allow_flat=False
        )

        # Build a base queryset compatible with this filter
        def _get_base_queryset():
            try:
                if hasattr(block_impl, "get_base_queryset"):
                    qs = block_impl.get_base_queryset(request.user)
                elif cfg.get("model") is not None:
                    qs = cfg["model"].objects.all()
                elif hasattr(block_impl, "get_model"):
                    qs = block_impl.get_model().objects.all()
                else:
                    qs = None
            except Exception:
                qs = None
            try:
                if qs is not None and hasattr(block_impl, "filter_queryset"):
                    qs = block_impl.filter_queryset(request.user, qs)
            except Exception:
                pass
            return qs

        base_qs = _get_base_queryset()

        def _apply_other_filters(qs):
            if qs is None:
                return None
            for k, scfg in raw_schema.items():
                if k == key:
                    continue
                if scfg.get("type") not in {"select", "multiselect"}:
                    continue
                val = current_filters.get(k)
                if val is None or val == "":
                    continue
                handler = scfg.get("handler")
                if callable(handler):
                    try:
                        qs = handler(qs, val)
                    except Exception:
                        pass
            return qs

        if base_qs is not None:
            try:
                base_qs = _apply_other_filters(base_qs)
            except Exception:
                pass

        value_path = cfg.get("value_path") or cfg.get("field")
        allowed_ids: Optional[Set[str]] = None
        if base_qs is not None and value_path:
            try:
                raw_vals: Iterable = base_qs.values_list(value_path, flat=True).distinct()
                allowed_ids = {str(v) for v in raw_vals if v not in (None, "")}
            except Exception:
                allowed_ids = None

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

                # Compute ids to constrain choice callable
                # - For label hydration (ids provided), always pass ids (intersected with allowed)
                # - For normal fetch with no query, we can pass allowed ids (capped) for efficiency
                # - For typed queries, DO NOT pass ids; let the callable search globally,
                #   then we will intersect results with allowed_ids after.
                ids_for_callable: Optional[list[str]] = None
                if raw_tokens:
                    ids_for_callable = raw_tokens
                    if allowed_ids is not None:
                        ids_for_callable = [v for v in ids_for_callable if v in allowed_ids]
                elif not query and allowed_ids is not None:
                    ids_for_callable = list(sorted(allowed_ids))[: self.MAX_OPTIONS]

                if "ids" in params and ids_for_callable is not None:
                    kwargs["ids"] = ids_for_callable

                choices = choices_callable(*args, **kwargs)

                # If the callable doesn't support ids narrowing, or we didn't pass ids
                # for typed queries, intersect here to enforce allowed set
                if allowed_ids is not None and not raw_tokens:
                    choices = [(v, lbl) for (v, lbl) in choices if str(v) in allowed_ids]
            except Exception:
                choices = []
        elif isinstance(cfg.get("choices"), (list, tuple)):
            choices = cfg.get("choices")

        q_lower = (query or "").lower()
        for value, label in choices[: self.MAX_OPTIONS]:
            if allowed_ids is not None and str(value) not in allowed_ids and not raw_tokens:
                continue
            label_str = str(label)
            if not query or q_lower in label_str.lower():
                results.append({"value": value, "label": label_str})
        return JsonResponse(results, safe=False)
