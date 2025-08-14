# Permissions

## Cache clearing

`apps.permissions.checks` caches calls to `User.has_perm` for the life of a
request. To avoid cache leakage between requests you must clear this cache
either via Django's `request_finished` signal or by using the middleware.
The signal hook is registered automatically when `apps.permissions` is in
`INSTALLED_APPS`. If you prefer middleware, add it to your `MIDDLEWARE`
setting:

```python
MIDDLEWARE = [
    # ...
    "apps.permissions.middleware.PermissionCacheMiddleware",
]
```

Either the middleware or the signal hook must be enabled to prevent
unbounded cache growth.

## Permission Template Tags

This project exposes template tags that mirror the utilities in
`apps.permissions.checks`. They allow model-, instance-, and field-level
permission checks directly in Django templates so you can conditionally render
UI elements.

```django
{% load permissions_tags %}

{# Model-level check #}
{% if user_can_add_model MyModel %}
    <a href="{% url 'mymodel_add' %}">Add Model</a>
{% endif %}

{# Instance-level check #}
{% if user_can_change_instance object %}
    <a href="{% url 'mymodel_edit' object.pk %}">Edit</a>
{% endif %}

{# Field-level check without an instance #}
{% if user_can_read MyModel 'status' %}
    {{ object.status }}
{% endif %}

{# Field-level check honoring instance-level permissions #}
{% if user_can_write MyModel 'status' object %}
    <!-- render editable field -->
{% endif %}
```

All of these tags delegate to similarly named functions in
`apps.permissions.checks` and return booleans indicating whether the request's
user has the requisite permission. If you need to check permissions for a
different user, pass them as the first argument to the tag.
