# Permissions

## Cache-clearing middleware

`apps.permissions.checks` caches calls to `User.has_perm` for the life of a
request. To ensure fresh results between requests, add the middleware to your
`MIDDLEWARE` setting:

```python
MIDDLEWARE = [
    # ...
    "apps.permissions.middleware.PermissionCacheMiddleware",
]
```

## Permission Template Tags

This project exposes template tags that mirror the utilities in
`apps.permissions.checks`. They allow model-, instance-, and field-level
permission checks directly in Django templates so you can conditionally render
UI elements.

```django
{% load permissions_tags %}

{# Model-level check #}
{% if user_can_add_model request.user MyModel %}
    <a href="{% url 'mymodel_add' %}">Add Model</a>
{% endif %}

{# Instance-level check #}
{% if user_can_change_instance request.user object %}
    <a href="{% url 'mymodel_edit' object.pk %}">Edit</a>
{% endif %}

{# Field-level check without an instance #}
{% if user_can_read request.user MyModel 'status' %}
    {{ object.status }}
{% endif %}

{# Field-level check honoring instance-level permissions #}
{% if user_can_write request.user MyModel 'status' object %}
    <!-- render editable field -->
{% endif %}
```

All of these tags delegate to similarly named functions in
`apps.permissions.checks` and return booleans indicating whether the `user` has
the requisite permission.
