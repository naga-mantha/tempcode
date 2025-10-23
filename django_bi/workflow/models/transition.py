from django.db import models
from django.contrib.auth.models import Group
from django_bi.conf import settings
from django_bi.workflow.models import Workflow, State

class Transition(models.Model):
    workflow = models.ForeignKey(Workflow, on_delete=models.PROTECT, related_name="transitions")
    name = models.CharField(max_length=100)
    source_state = models.ForeignKey(State, on_delete=models.PROTECT, related_name="transitions_from")
    dest_state = models.ForeignKey(State, on_delete=models.PROTECT, related_name="transitions_to")
    allowed_groups = models.ManyToManyField(Group, blank=True, help_text="Which user groups may trigger this")

    objects = models.Manager()

    class Meta:
        unique_together = ("workflow", "source_state", "dest_state", "name")

    def __str__(self):
        return f"{self.workflow.name}: {self.source_state.name} → {self.dest_state.name} ({self.name})"

    def is_allowed_for_user(self, user):
        if getattr(user, "is_superuser", False):
            return True
        staff_bypass = getattr(settings, "PERMISSIONS_STAFF_BYPASS", True)
        if staff_bypass and getattr(user, "is_staff", False):
            return True
        return user.groups.filter(id__in=self.allowed_groups.values_list("id", flat=True)).exists()
