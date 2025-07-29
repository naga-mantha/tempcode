from django.db import models
from apps.workflow.models import Workflow, State

class WorkflowModelMixin(models.Model):
    workflow = models.ForeignKey(Workflow, on_delete=models.PROTECT)
    workflow_state = models.ForeignKey(State, on_delete=models.PROTECT)

    class Meta:
        abstract = True

    def get_workflow(self):
        return self.workflow

    def get_workflow_state(self):
        return self.workflow_state
