from django.urls import path
from .views import *


urlpatterns = [path('so_validate',  so_validate , name='so_validate'),]
