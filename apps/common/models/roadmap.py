from django.db import models


class Roadmap(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"

    class Timeframe(models.TextChoices):
        Q1 = "Q1", "Q1"
        Q2 = "Q2", "Q2"
        Q3 = "Q3", "Q3"
        Q4 = "Q4", "Q4"

    class App(models.TextChoices):
        COMMON = "Common", "Common"
        WORKFLOWS = "Workflows", "Workflows"
        PERMISSIONS = "Permissions", "Permissions"
        LAYOUTS = "Layouts", "Layouts"
        PURCHASE = "Purchase", "Purchase"
        PRODUCTION = "Production", "Production"
        SALES = "Sales", "Sales"
        PLANNING = "Planning", "Planning"
        SERVICE = "Service", "Service"
        TABLE = "Table", "Table"
        PIVOT = "Pivot", "Pivot"
        PIE = "Pie", "Pie"
        BAR = "Bar", "Bar"
        LINE = "Line", "Line"
        DIAL = "Dial", "Dial"
        KANBAN = "Kanban", "Kanban"
        GANNT = "Gannt", "Gannt"
        REPEATER = "Repeater", "Repeater"
        SPACER = "Spacer", "Spacer"
        TEXT = "Text", "Text"
        FORM = "Form", "Form"
        BUTTON = "Button", "Button"
        LIST = "List", "List"

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    technical_specifications = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)
    timeframe = models.CharField(max_length=2, choices=Timeframe.choices)
    app = models.CharField(max_length=20, choices=App.choices)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["app", "timeframe", "title"]

    def __str__(self) -> str:
        return f"{self.title} ({self.app} / {self.timeframe})"
