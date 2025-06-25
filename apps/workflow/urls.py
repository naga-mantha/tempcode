from django.urls import path
from apps.workflow.views.autocomplete import ContentTypeAutocomplete, FieldNameAutocomplete

app_name = 'workflow'
urlpatterns = [
    path('autocomplete/contenttype/', ContentTypeAutocomplete.as_view(), name='contenttype-autocomplete'),
    path('autocomplete/field-name/', FieldNameAutocomplete.as_view(), name='fieldname-autocomplete'),
]
