from django.db import models
from apps.common.models import ProductionOrderOperation, Machine
from apps.workflow.models import WorkflowModel, Workflow, State
from django_pandas.managers import DataFrameManager

class ProductionOrderSchedule(WorkflowModel):
    SCHEDULE_STATES = [
        ("unscheduled", "Unscheduled"),
        ("scheduled", "Scheduled"),
    ]

    # ToDo: Add remaining status from INFOR
    EXECUTION_STATES = [
        ("planned", "Planned"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("late", "Late"),
    ]

    operation = models.ForeignKey(ProductionOrderOperation, on_delete=models.PROTECT, related_name="schedule")
    start_datetime = models.DateTimeField(blank=True, null=True)
    end_datetime = models.DateTimeField(blank=True, null=True)
    machine = models.ForeignKey(Machine, on_delete=models.PROTECT, blank=True, null=True)
    schedule_state = models.CharField(max_length=20, choices=SCHEDULE_STATES, default="unscheduled")
    execution_state = models.CharField(max_length=20, choices=EXECUTION_STATES, default="planned")
    workflow = models.ForeignKey(Workflow, on_delete=models.PROTECT, blank=True, null=True)
    state = models.ForeignKey(State, on_delete=models.PROTECT, blank=True, null=True)

    objects = models.Manager()
    df_objects = DataFrameManager()

    class Meta:
        ordering = ["start_datetime"]

    def __str__(self):
        return f"{self.operation} scheduled from {self.start_datetime} to {self.end_datetime}"
