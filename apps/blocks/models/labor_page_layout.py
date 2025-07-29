from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class LaborPageLayout(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    layout_json = models.JSONField()  # [{"id": "labor_form", "layout": "row"}, ...]
    is_default = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
