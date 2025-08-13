# Permission Template Tags

This project exposes template tags to perform field-level permission checks in Django templates.

```django
{% load permissions_tags %}

{# Basic field check without an instance #}
{% if user_can_read request.user MyModel 'status' %}
    {{ object.status }}
{% endif %}

{# Instance-aware check #}
{% if user_can_write request.user MyModel 'status' object %}
    <!-- render editable field -->
{% endif %}
```

Both `user_can_read` and `user_can_write` accept an optional `instance` argument to apply instance-level permission logic.
