# Django Blocks App

`django-blocks-app` packages the dynamic block registry, templates, and helper services
from the `apps.blocks` module so they can be reused across Django projects. The
package exposes reusable tables, pivots, and UI blocks that can be registered at
runtime.

## Installation

```
pip install django-blocks-app
```

Add the app to your Django settings:

```
INSTALLED_APPS = [
    # ...
    "apps.blocks",
]
```

Run the database migrations to set up the required tables:

```
python manage.py migrate blocks
```

## Registering Blocks

Use the registry helpers under `apps.blocks.registry` to define custom table or
pivot specifications. Refer to the templates shipped within the package for
examples of how to render block outputs.

## Packaging Notes

This repository now includes packaging metadata via `pyproject.toml` and
`MANIFEST.in` so the Blocks app can be built as an installable distribution.
Templates, static assets, migrations, and management commands are included in the
wheel automatically.
