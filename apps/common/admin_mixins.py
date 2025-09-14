from django.contrib import admin


class BaseAutoComputeAdmin(admin.ModelAdmin):
    """Base admin that forwards auto-compute policy kwargs to model.save().

    Override get_auto_compute_save_kwargs to customize per model/user.
    You may also set class attributes:
      - auto_compute_recalc
      - auto_compute_recalc_exclude
    """

    auto_compute_recalc = None
    auto_compute_recalc_exclude = None

    def get_auto_compute_save_kwargs(self, request, obj, form, change):
        kwargs = {}
        if self.auto_compute_recalc is not None:
            kwargs["recalc"] = self.auto_compute_recalc
        if self.auto_compute_recalc_exclude is not None:
            kwargs["recalc_exclude"] = self.auto_compute_recalc_exclude
        return kwargs

    def save_model(self, request, obj, form, change):
        save_kwargs = self.get_auto_compute_save_kwargs(request, obj, form, change) or {}
        obj.save(**save_kwargs)

