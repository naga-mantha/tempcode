from datetime import date, timedelta
from calendar import monthrange
from apps.common.models import GlobalSettings


class FilterResolutionMixin:
    """Common filter resolution helpers for table blocks and views."""

    @staticmethod
    def _resolve_filter_schema(raw_schema, user):
        """Normalize raw filter schema and resolve callable choices."""
        schema = {}
        for key, cfg in raw_schema.items():
            item = dict(cfg)
            item.setdefault("type", "text")
            if "choices" in item and callable(item["choices"]):
                # If an ajax URL is provided, defer resolving choices until
                # requested by the client.
                if item.get("choices_url"):
                    item["choices"] = []
                else:
                    item["choices"] = item["choices"](user)
            schema[key] = item
        return schema

    @staticmethod
    def _collect_filters(qd, schema, base=None, *, prefix="filters.", allow_flat=True, resolve_tokens=True):
        """Collect filter values from a QueryDict overlaying optional base values.

        When ``resolve_tokens`` is True (default), special date tokens like
        "__today__" are expanded to concrete ISO dates. When False, tokens are
        preserved as provided so they can be stored in saved filter configs and
        evaluated at runtime later.
        """
        base = dict(base or {})

        def _resolve_token(val):
            if not isinstance(val, str):
                return val
            token = val.strip().lower()
            today = date.today()
            if token in {"__today__", "today"}:
                return today.isoformat()
            if token in {"__start_of_month__", "start_of_month"}:
                return today.replace(day=1).isoformat()
            if token in {"__end_of_month__", "end_of_month"}:
                last_day = monthrange(today.year, today.month)[1]
                return today.replace(day=last_day).isoformat()
            if token in {"__start_of_year__", "start_of_year"}:
                return today.replace(month=1, day=1).isoformat()
            if token in {"__end_of_year__", "end_of_year"}:
                return today.replace(month=12, day=31).isoformat()
            if token in {"__start_of_quarter__", "start_of_quarter"}:
                q = (today.month - 1) // 3
                start_month = q * 3 + 1
                return today.replace(month=start_month, day=1).isoformat()
            if token in {"__end_of_quarter__", "end_of_quarter"}:
                q = (today.month - 1) // 3
                end_month = q * 3 + 3
                last_day = monthrange(today.year, end_month)[1]
                return today.replace(month=end_month, day=last_day).isoformat()
            # Fiscal year tokens from GlobalSettings
            if token in {
                "__current_fiscal_year_start__",
                "current_fiscal_year_start",
                "fiscal_year_start",
            } or token.startswith("__fy_start__"):
                gs = GlobalSettings.objects.first()
                fy_month = (gs.fiscal_year_start_month if gs else 1) or 1
                fy_day = (gs.fiscal_year_start_day if gs else 1) or 1
                start_candidate = date(today.year, fy_month, fy_day)
                if today < start_candidate:
                    start_candidate = date(today.year - 1, fy_month, fy_day)
                return start_candidate.isoformat()
            if token in {
                "__current_fiscal_year_end__",
                "current_fiscal_year_end",
                "fiscal_year_end",
            } or token.startswith("__fy_end__"):
                gs = GlobalSettings.objects.first()
                fy_month = (gs.fiscal_year_start_month if gs else 1) or 1
                fy_day = (gs.fiscal_year_start_day if gs else 1) or 1
                start_candidate = date(today.year, fy_month, fy_day)
                if today < start_candidate:
                    start_candidate = date(today.year - 1, fy_month, fy_day)
                next_start = date(start_candidate.year + 1, fy_month, fy_day)
                return (next_start - timedelta(days=1)).isoformat()
            return val

        # Pre-resolve any dynamic tokens in provided base values
        if resolve_tokens:
            for k, v in list(base.items()):
                base[k] = _resolve_token(v)
        if not schema:
            return base

        TRUTHY = {"1", "true", "on", "yes", "y", "t"}

        for key, cfg in schema.items():
            names = [f"{prefix}{key}"]
            if allow_flat:
                names.append(key)

            for name in names:
                if cfg.get("type") in {"multiselect"} and cfg.get("multiple"):
                    vals = qd.getlist(name)
                    if vals:
                        base[key] = vals
                        break
                elif cfg.get("type") == "boolean":
                    if name in qd:
                        base[key] = (qd.get(name) or "").strip().lower() in TRUTHY
                        break
                else:
                    raw = qd.get(name)
                    if raw not in (None, ""):
                        if resolve_tokens and cfg.get("type") in {"date", "text"}:
                            base[key] = _resolve_token(raw)
                        else:
                            base[key] = raw
                        break
        return base
