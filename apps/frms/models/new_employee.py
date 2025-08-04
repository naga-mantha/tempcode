from django.db import models
from apps.accounts.models import CustomUser
from apps.workflow.models import WorkflowModelMixin
from django.urls import reverse

class NewEmployee(WorkflowModelMixin):
    first_name = models.CharField(max_length=100, default="")
    last_name = models.CharField(max_length=100, default="")
    submitted_by = models.ForeignKey(CustomUser, blank=True, null=True, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    def __str__(self):
        """String for representing the Model object."""
        return str(self.first_name)

    def get_absolute_url(self):
        return reverse('new_employee_detail', kwargs={'pk': self.pk})
