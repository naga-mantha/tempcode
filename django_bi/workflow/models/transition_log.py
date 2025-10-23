from django.db import models
from django_bi.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django_bi.workflow.models import State, Transition

class TransitionLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    from_state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, related_name="+")
    to_state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, related_name="+")
    transition = models.ForeignKey(Transition, on_delete=models.SET_NULL, null=True)

    comment = models.TextField(blank=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.content_object} — {self.from_state} → {self.to_state} by {self.user}"
