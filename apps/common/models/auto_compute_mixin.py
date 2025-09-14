from django.db import models


class AutoComputeMixin(models.Model):
    """Mixin to manage auto-computed fields with opt-in policy control.

    Usage:
    - Define AUTO_COMPUTE = {"field_name": "compute_method_name", ...}
    - Implement compute methods on the model (e.g., compute_field_name).

    Policy kwargs accepted by save():
    - recalc: "all" (default), "none", or an iterable of field names to compute
    - recalc_exclude: iterable of field names to exclude from computation
    """

    AUTO_COMPUTE = {}

    class Meta:
        abstract = True

    def _normalize_fields_iterable(self, value):
        if value in (None, "", []):
            return set()
        if isinstance(value, str):
            return {value}
        return set(value)

    def _compute_fields(self, fields_to_compute):
        mapping = getattr(self, "AUTO_COMPUTE", {}) or {}
        for field in fields_to_compute:
            method_name = mapping.get(field)
            if not method_name:
                continue
            method = getattr(self, method_name, None)
            if not callable(method):
                continue
            setattr(self, field, method())

    def save(self, *args, **kwargs):
        recalc = kwargs.pop("recalc", "all")
        recalc_exclude = self._normalize_fields_iterable(kwargs.pop("recalc_exclude", set()))

        mapping = getattr(self, "AUTO_COMPUTE", {}) or {}

        if recalc == "none":
            fields_to_compute = set()
        elif recalc == "all":
            fields_to_compute = set(mapping.keys())
        else:
            fields_to_compute = self._normalize_fields_iterable(recalc)

        fields_to_compute -= recalc_exclude

        if fields_to_compute:
            self._compute_fields(fields_to_compute)

        super().save(*args, **kwargs)

