class FilterResolutionMixin:
    """Common filter resolution helpers for table blocks and views."""

    @staticmethod
    def _resolve_filter_schema(raw_schema, user):
        """Normalize raw filter schema and resolve callable choices."""
        schema = {}
        for key, cfg in raw_schema.items():
            item = dict(cfg)
            item.setdefault("type", "text")
            if item["type"] == "autocomplete":
                item.setdefault("multiple", False)
            if "choices" in item and callable(item["choices"]):
                item["choices"] = item["choices"](user)
            schema[key] = item
        return schema

    @staticmethod
    def _collect_filters(qd, schema, base=None, *, prefix="filters.", allow_flat=True):
        """Collect filter values from a QueryDict overlaying optional base values."""
        base = dict(base or {})
        if not schema:
            return base

        TRUTHY = {"1", "true", "on", "yes", "y", "t"}

        for key, cfg in schema.items():
            names = [f"{prefix}{key}"]
            if allow_flat:
                names.append(key)

            for name in names:
                if cfg.get("type") in {"multiselect", "autocomplete"} and cfg.get("multiple"):
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
                        base[key] = raw
                        break
        return base
