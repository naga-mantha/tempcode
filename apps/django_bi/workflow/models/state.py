from django.db import models
from apps.django_bi.workflow.models import Workflow

class State(models.Model):
    workflow = models.ForeignKey(Workflow, on_delete=models.PROTECT, related_name="states")
    name = models.CharField(max_length=100, verbose_name="WF State Name")
    is_start = models.BooleanField(default=False, verbose_name="WF State Start")
    is_end = models.BooleanField(default=False, verbose_name="WF State End")

    objects = models.Manager()

    class Meta:
        unique_together = ("workflow", "name")

    def __str__(self):
        return f"{self.workflow.name}: {self.name}"

    def save(self, *args, **kwargs):
        creating = self._state.adding

        super().save(*args, **kwargs)  # Save first so we get an ID

        # First state for this workflow → force is_start = True
        if creating and not self.workflow.states.exclude(pk=self.pk).exists():
            if not self.is_start:
                self.is_start = True
                super().save(update_fields=["is_start"])

        # If user marks this state as start, demote others in same workflow
        elif self.is_start:
            self.workflow.states.exclude(pk=self.pk).filter(is_start=True).update(is_start=False)
