from django.db import models
from apps.accounts.models import CustomUser
from apps.workflow.models import WorkflowModel, Workflow, State
from django.urls import reverse

class NewEmployee(WorkflowModel):
    first_name = models.CharField(max_length=100, default="")
    last_name = models.CharField(max_length=100, default="")
    submitted_by = models.ForeignKey(CustomUser, blank=True, null=True, on_delete=models.PROTECT)
    workflow = models.ForeignKey(Workflow, on_delete=models.PROTECT, blank=True, null=True, help_text="Which workflow definition this record uses")
    state = models.ForeignKey(State, on_delete=models.PROTECT, blank=True, null=True, help_text="Current state in the workflow")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    def __str__(self):
        """String for representing the Model object."""
        return str(self.first_name)

    def get_absolute_url(self):
        return reverse('new_employee_detail', kwargs={'pk': self.pk})
