from django.db import models


class ToDo(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = "Not Started", "Not Started"
        IN_PROGRESS = "In Progress", "In Progress"
        COMPLETED = "Completed", "Completed"

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_STARTED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    priority = models.IntegerField(default=999, db_index=True)
    dependencies = models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=False,
        related_name="dependents",
    )

    class Meta:
        ordering = ["priority", "created_at"]

    def __str__(self) -> str:
        return self.title

    @property
    def bs_class(self) -> str:
        if self.status == self.Status.IN_PROGRESS:
            return "primary"
        if self.status == self.Status.COMPLETED:
            return "success"
        return "secondary"
