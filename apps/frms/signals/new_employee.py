from django.db.models.signals import pre_save
from django.dispatch import receiver
from apps.frms.models import NewEmployee
from apps.workflow.models import State

@receiver(pre_save, sender=NewEmployee)
def set_employee_initial_state(sender, instance, **kwargs):
    pass
    # if instance._state.adding and not instance.state_id:
    #     print(instance.workflow)
    #     # grab the draft/start state for this workflow
    #     start = State.objects.get(workflow=instance.workflow, is_start=True)
    #     instance.state = start
