from django.urls import path
from .views import *
from apps.workflow.views import apply_transition

urlpatterns = [
    path('new_employee/form', new_employee, name='new_employee_form'),
    path('new_employee/list', new_employee_list, name='new_employee_list'),
    path('new_employee/<int:pk>/', new_employee_detail, name='new_employee_detail'),
    path("new-employee/<int:pk>/transition/",
         apply_transition,
         {"app_label": "frms", "model_name": "newemployee", "redirect_url_name": "new_employee_detail"},
         name="apply_transition",
    ),
]