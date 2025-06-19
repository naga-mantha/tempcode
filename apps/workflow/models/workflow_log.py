from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from apps.workflow.models import Transition
from apps.accounts.models import CustomUser

class WorkflowLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    transition = models.ForeignKey(Transition, on_delete=models.CASCADE)
    comment = models.TextField(blank=True)

    # Generic relation to the “document” being transitioned:
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_obj = GenericForeignKey("content_type", "object_id")

    objects = models.Manager()

    def __str__(self):
        return (f"{self.timestamp:%Y-%m-%d %H:%M} — "
                f"{self.content_obj} — {self.transition.name} by {self.user}")
