# NOT NEEDED ANYMORE



from django.db import models
from django.contrib.contenttypes.models import ContentType
from apps.workflow.models import Workflow, State, Transition, WorkflowLog
from apps.workflow.views.permissions import can_write_field

class WorkflowModel(models.Model):
    """
    Abstract base:
    - Adds workflow + state FKs
    - Provides get_available_transitions() & do_transition()
    - Enforces both static (Django-perm) and dynamic (state-based) checks
    """
    workflow = models.ForeignKey(Workflow, on_delete=models.PROTECT, help_text="Which workflow definition applies")
    state = models.ForeignKey(State, on_delete=models.PROTECT, help_text="Current state in the workflow")

    class Meta:
        abstract = True

    def get_available_transitions(self, user):
        if user.is_superuser:
            return Transition.objects.filter(workflow=self.workflow, source_state=self.state)

        if self.workflow.status == Workflow.INACTIVE:
            return Transition.objects.none()

        return (Transition.objects.filter(workflow=self.workflow, source_state=self.state, allowed_groups__in=user.groups.all()).distinct())

    def do_transition(self, transition, user, comment=""):
        if self.workflow.status == Workflow.INACTIVE:
            raise PermissionError("Cannot transition: workflow is inactive.")

        if not user.is_superuser:
            if transition.source_state != self.state:
                raise ValueError("Invalid transition for this state.")
            if not user.groups.filter(pk__in=transition.allowed_groups.values_list("pk", flat=True)).exists():
                raise PermissionError("You are not allowed to perform this transition.")

        self.state = transition.dest_state
        self.save(update_fields=["state"])

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
          2) Static model‐level via Django's 'change_modelname' perm
          3) Dynamic state‐level via allowed_groups on the current state
        """
        if user.is_superuser:
            return True

        # static: do they have the 'change' perm on this model?
        app_label = self._meta.app_label
        model_name = self._meta.model_name
        perm_str = f"{app_label}.change_{model_name}"
        if not user.has_perm(perm_str):
            return False

        # dynamic: if a workflow is set, check state.allowed_groups
        if self.workflow:
            if self.workflow.status == Workflow.INACTIVE:
                return False
            allowed = self.state.allowed_groups.all()
            if not allowed.exists():
                return True
            return user.groups.filter(pk__in=allowed.values_list("pk", flat=True)).exists()

        # no workflow → static passed → allow
        return True

    def can_edit_field(self, user, field_name):
        """
        Field‐level edit check:
          1) Superuser bypass
          2) Django 'change_<model>_<field>' perm
          3) Workflow state‐level via State.allowed_groups
        """
        # 1) Superuser bypass
        if user.is_superuser:
            return True

        # 2) Static field‐level perm
        if not can_write_field(user, self, field_name):
            return False

        # 3) Dynamic: if a workflow is set, enforce state.allowed_groups
        if self.workflow:
            # no edits when workflow is inactive
            if self.workflow.status == Workflow.INACTIVE:
                return False

            allowed = self.state.allowed_groups.all()
            # if no groups configured → everyone with the change perm may edit
            if not allowed.exists():
                return True

            # otherwise only those in allowed_groups
            return user.groups.filter(pk__in=allowed.values_list("pk", flat=True)).exists()

        # No workflow defined → static perm was enough
        return True
