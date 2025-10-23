# Django BI Integration

This project packages the `django_bi` reusable Django application along with a
sample MAG360 project configuration. Use it as a reference for adding the
analytics dashboards to your own site.

## Requirements

* Python 3.12+
* Django 5.2
* Node.js (for building the front-end assets shipped with `django_bi`)

Create and activate a virtual environment, then install the dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Install the JavaScript packages that power the dashboard widgets:

```bash
npm install
```

## Example environment variables

The MAG360 settings rely on `django-environ` to load configuration from a
`.env` file. Copy the snippet below to `.env` in the project root and adjust the
values for your environment:

```dotenv
SECRET_KEY=change-me
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
SITE_ID=1

DATABASE_ENGINE=django.db.backends.sqlite3
DATABASE_NAME=db.sqlite3
# PostgreSQL example:
# DATABASE_ENGINE=django.db.backends.postgresql
# DATABASE_NAME=mag360
# DATABASE_USER=mag360
# DATABASE_PASS=super-secret
# DATABASE_HOST=127.0.0.1
# DATABASE_PORT=5432

COMPANY_FULL_NAME=Acme Industries
BI_FISCAL_YEAR_START_MONTH=10
BI_FISCAL_YEAR_START_DAY=1
ADMINS="Support <support@example.com>"
EMAIL_HOST=localhost
DEFAULT_FROM_EMAIL=no-reply@example.com
```

## Example Django settings

Add the application, middleware, templates, and static configuration to your
`settings.py` (or adapt the snippet for another settings module):

```python
INSTALLED_APPS = [
    # Project apps…
    "django_bi",
    "django_comments",          # Required for comments support
    "django_comments_xtd",      # Extended comment threading
    "crispy_forms",
    "crispy_bootstrap5",
    "widget_tweaks",
]

MIDDLEWARE = [
    # …existing middleware…
    "django_bi.permissions.middleware.PermissionCacheMiddleware",
]

TEMPLATES[0]["DIRS"].extend([
    BASE_DIR / "django_bi" / "layout" / "templates",
    BASE_DIR / "django_bi" / "blocks" / "templates",
])
TEMPLATES[0]["OPTIONS"]["context_processors"].extend([
    "django_bi.utils.context_processors.sidebar_layouts",
    "django_bi.utils.context_processors.branding",
])

STATIC_URL = "dist/"
STATIC_ROOT = BASE_DIR / "dist"
STATICFILES_DIRS = [BASE_DIR / "django_bi" / "dist"]

BI_FISCAL_YEAR_START_MONTH = 10
BI_FISCAL_YEAR_START_DAY = 1
PERMISSIONS_STAFF_BYPASS = False
COMPANY_FULL_NAME = "Acme Industries"
```

## URL inclusion

Wire the dashboards into your project-level URL configuration. The snippet
below shows how MAG360 exposes the workflow, block, and layout views provided by
`django_bi`:

```python
from django.urls import include, path

urlpatterns = [
    # Existing routes…
    path("workflow/", include("django_bi.workflow.urls", namespace="workflow")),
    path("blocks/", include("django_bi.blocks.urls", namespace="blocks")),
    path("layouts/", include("django_bi.layout.urls", namespace="layout")),
]
```

If your project already uses the same prefixes, adjust them to avoid clashes
while keeping the namespaces intact.

## Database migrations

Run the Django migrations after configuring your settings and URLs. The
commands below create the database tables for `django_bi` and the accompanying
MAG360 applications:

```bash
python manage.py migrate
```

If you make changes to any of the models in `apps.*` or `django_bi`, create new
migration files and apply them:

```bash
python manage.py makemigrations apps.accounts apps.production django_bi
python manage.py migrate
```

## Running the project locally

Compile the front-end assets (when needed) and start the Django development
server:

```bash
npm run build
python manage.py runserver
```

The dashboard should now be accessible at `http://127.0.0.1:8000/`.
