from django import forms
from apps.frms.models import NewEmployee
from apps.workflow.models import Workflow, State
from django import forms
from apps.workflow.views.permissions import FieldLevelFormMixin
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Fieldset, Div, Row, Column, Button
from crispy_forms.bootstrap import FormActions

class NewEmployeeForm(FieldLevelFormMixin, forms.ModelForm):
    class Meta:
        model = NewEmployee
        fields = ['first_name', 'last_name', 'workflow']

    def __init__(self, *args, user=None, exclude_workflow=False, **kwargs):
        # Pass `user` into the mixin, so it can hide/disable fields
        super().__init__(*args, user=user, **kwargs)

        if exclude_workflow:
            self.fields.pop('workflow', None)
        else:
            # Only Active workflows can be chosen when creating new records
            self.fields['workflow'].queryset = Workflow.objects.filter(status=Workflow.ACTIVE)

        # === Crispy setup ===
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column("first_name", css_class="mb-3"),
                Column("last_name", css_class="mb-3"),
            ),
            Row(
                Column("workflow", css_class="sm-12"),
            ) if not exclude_workflow else Div(),

            FormActions(
                Submit('update_new_employee', 'Save changes', css_class="btn btn-success"),
            )
        )

    def clean_workflow(self):
        wf = self.cleaned_data.get('workflow')
        if wf and wf.status != Workflow.ACTIVE:
            raise forms.ValidationError(
                "You may only start a record under an Active workflow."
            )
        return wf

    def save(self, commit=True):
        # First, get the partially populated instance (with workflow set)
        obj = super().save(commit=False)

        # If it’s a new record and state isn’t set yet, assign the correct start-state
        if not obj.pk and not obj.state_id:
            try:
                start = State.objects.get(workflow=obj.workflow, is_start=True)
            except State.DoesNotExist:
                raise forms.ValidationError(
                    f"No start-state defined for workflow '{obj.workflow.name}'."
                )
            obj.state = start

        if commit:
            obj.save()

        return obj