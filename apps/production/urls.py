from django.urls import path
from . import views


urlpatterns = [
    path("item-autocomplete/", views.ItemAutocomplete.as_view(), name="item-autocomplete"),
]