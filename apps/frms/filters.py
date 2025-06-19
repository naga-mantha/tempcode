# apps/employee/filters.py

from django.utils.timezone import now
from datetime import timedelta

def get_filter_schema():
    return {
        "first_name": {
            "label": "Search First Name",
            "input_type": "text",
            "handler": filter_by_first_name,
        },
    }

def filter_by_first_name(queryset, value):
    if not value:
        return queryset

    return queryset.filter(first_name=value)
