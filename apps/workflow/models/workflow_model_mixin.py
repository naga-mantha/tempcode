from django.db import models
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
        # Assign start state if it's a new object and state not already set
        if not self.pk and self.workflow and not self.workflow_state:
            self.workflow_state = self.workflow.states.filter(is_start=True).first()
        super().save(*args, **kwargs)
