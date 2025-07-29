from django.urls import path
from apps.workflow.views.transition import perform_transition

app_name = 'workflow'
urlpatterns = [
    path(
        "transition/<str:app_label>/<str:model_name>/<int:object_id>/<str:transition_name>/",
        perform_transition,
        name="workflow_perform_transition"
    ),
]