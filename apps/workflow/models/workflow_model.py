from django.db import models
from django.contrib.contenttypes.models import ContentType
from apps.workflow.models import Workflow, State, Transition, WorkflowLog
from apps.workflow.views.permissions import has_model_permission, has_field_permission
from django.core.exceptions import PermissionDenied

class WorkflowModel(models.Model):
    """
    Abstract base: pulls in the workflow+state FKs
    and provides get_available_transitions() & do_transition().
    """
    workflow = models.ForeignKey(Workflow, on_delete=models.PROTECT, help_text="Which workflow definition applies")
    state = models.ForeignKey(State, on_delete=models.PROTECT, help_text="Current state in the workflow")

    class Meta:
        abstract = True

    def get_available_transitions(self, user):
        # If admin, show _all_ transitions regardless of allowed_groups
        if user.is_superuser:
            return Transition.objects.filter(
                workflow=self.workflow,
                source_state = self.state,
            )

        # No actions if the workflow is Inactive
        if self.workflow.status == Workflow.INACTIVE:
            return Transition.objects.none()

        return Transition.objects.filter(
            workflow=self.workflow,
            source_state=self.state,
            allowed_groups__in=user.groups.all()
        ).distinct()

    def do_transition(self, transition, user, comment=""):
        # Block inactive flows for everyone
        if self.workflow.status == Workflow.INACTIVE:
            raise PermissionError("Cannot transition: workflow is inactive.")

       # Admins can always transition
        if not user.is_superuser:
            if transition.source_state != self.state:
                raise ValueError("Invalid transition for this state.")
            if not user.groups.filter(pk__in=transition.allowed_groups.values_list("pk", flat=True)).exists():
                raise PermissionError("You are not allowed to perform this transition.")

        # move to new state
        self.state = transition.dest_state
        self.save(update_fields=["state"])
        # log it
        WorkflowLog.objects.create(
            user=user,
            transition=transition,
            comment=comment,
            content_type=ContentType.objects.get_for_model(self),
            object_id=self.pk,
        )

    def can_edit(self, user):
        """
        Record‐level edit check:
          1) Superuser bypass
          2) Static doctype‐level via has_model_permission(...)
          3) Dynamic workflow‐state: only allowed_groups in that state
        """

        # Superusers bypass all rules
        if user.is_superuser:
            return True

        # static: do they have CHANGE permission on this model?
        if not has_model_permission(user, self.__class__, "change"):
            return False

        # dynamic: if a workflow is set, check state.allowed_groups
        wf = getattr(self, "workflow", None)
        if wf:
            if wf.status == Workflow.INACTIVE:
                return False
            allowed = self.state.allowed_groups.all()
            if not allowed.exists():
                return True
            return user.groups.filter(pk__in=allowed.values_list("pk", flat=True)).exists()

        # 3) No workflow → static passed → allow
        return True

    def can_edit_field(self, user, field_name):
        """
        Field‐level edit check:
          1) Superuser bypass
          2) Static field‐level via has_field_permission(...)
          3) Dynamic state‐level override via State.field_perms or state.allowed_groups
        """

        # Superusers bypass all rules
        if user.is_superuser:
            return True

        # static: do they have WRITE permission on this field?
        if not has_field_permission(user, self, field_name, "write"):
            return False

        # 2) Dynamic state‐level (if workflow set)
        wf = getattr(self, "workflow", None)
        if wf:
            if wf.status == Workflow.INACTIVE:
                return False
            # first look for a FieldPermission override on this state
            fp = self.state.field_perms.filter(field_name=field_name).first()
            allowed = fp.allowed_groups.all() if fp else self.state.allowed_groups.all()
            if not allowed.exists():
                return True
            return user.groups.filter(pk__in=allowed.values_list("pk", flat=True)).exists()

        # 3) No workflow → static passed → allow
        return True
