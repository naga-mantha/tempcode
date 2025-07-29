from django.urls import path
from .views import *

urlpatterns = [
    path("labor-page/", labor_page, name="labor_page"),
]