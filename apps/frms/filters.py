from apps.layout.filter_registry import register

@register("newemployee")
def get_filter_schema():
    return {
        "first_name": {
            "label": "Search First Name",
            "input_type": "text",
            "handler": filter_by_first_name,
        },

        "last_name": {
            "label": "Search Last Name",
            "input_type": "text",
            "handler": filter_by_last_name,
        },
    }

def filter_by_first_name(queryset, value):
    if not value:
        return queryset

    return queryset.filter(first_name__contains=value)

def filter_by_last_name(queryset, value):
    if not value:
        return queryset

    return queryset.filter(last_name__contains=value)

