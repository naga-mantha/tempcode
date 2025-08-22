from django.db import models
from django.core.exceptions import PermissionDenied
from apps.workflow.models import Workflow, State

class WorkflowModelMixin(models.Model):
    workflow = models.ForeignKey(Workflow, on_delete=models.PROTECT, default=None, null=True)
    workflow_state = models.ForeignKey(State, on_delete=models.PROTECT, default=None, null=True)

    class Meta:
        abstract = True

    def get_workflow(self):
        return self.workflow

    def get_workflow_state(self):
        return self.workflow_state

    def save(self, *args, **kwargs):
        # Enforce creation rules based on workflow status
        if not self.pk and self.workflow:
            status = getattr(self.workflow, "status", None)
            if status == getattr(self.workflow, "DEPRECATED", "deprecated"):
                # Deprecated: block creation entirely
                raise PermissionDenied("This workflow is deprecated; new objects cannot be created.")
            if status == getattr(self.workflow, "INACTIVE", "inactive"):
                # Inactive: block creation entirely
                raise PermissionDenied("This workflow is inactive; new objects cannot be created.")

            # Assign start state if not already set
            if not self.workflow_state:
                self.workflow_state = self.workflow.states.filter(is_start=True).first()
        super().save(*args, **kwargs)
