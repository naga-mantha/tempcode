from django.urls import path
from . import views

urlpatterns = [
    path('run_scheduler', views.run_scheduler, name="run_scheduler"),
    path('gannt', views.gannt_page, name="gantt_view"),
]