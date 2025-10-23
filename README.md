# Django BI Integration

Django BI Integration bundles the reusable `django_bi` dashboards with a sample
MAG360 project configuration. Use it as a reference for wiring the analytics
suite into your own Django site or as a foundation for building an internal
business intelligence portal.

## Features

- **Reusable dashboards** – ready-to-use workflow, block, and layout views.
- **Configurable branding** – brand the navigation and dashboard chrome with
your company name.
- **Modern tooling** – includes both Python and Node.js dependencies required to
build the bundled assets.

## Requirements

- Python 3.12+
- Django 5.2
- Node.js 18+
- npm 9+

## Installation

1. Clone the repository and change into the project directory:

   ```bash
   git clone https://github.com/example/django-bi-integration.git
   cd django-bi-integration
   ```

2. Create and activate a virtual environment, then install the Python
   dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Install the JavaScript packages that power the dashboard widgets:

   ```bash
   npm install
   ```

4. Create a `.env` file using the template below and adjust the values for your
   environment:

   ```dotenv
   SECRET_KEY=change-me
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1
   SITE_ID=1

   DATABASE_ENGINE=django.db.backends.sqlite3
   DATABASE_NAME=db.sqlite3
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

5. Apply the database migrations and compile the front-end assets:

   ```bash
   python manage.py migrate
   npm run build
   ```

6. Start the Django development server:

   ```bash
   python manage.py runserver
   ```

The dashboards are now available at <http://127.0.0.1:8000/>.

## Usage examples

### Adding the app to an existing project

Add the required apps and middleware to your Django settings module:

```python
INSTALLED_APPS = [
    # Project apps…
    "django_bi",
    "django_comments",
    "django_comments_xtd",
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

Wire the dashboards into your project-level URL configuration:

```python
from django.urls import include, path

urlpatterns = [
    # Existing routes…
    path("workflow/", include("django_bi.workflow.urls", namespace="workflow")),
    path("blocks/", include("django_bi.blocks.urls", namespace="blocks")),
    path("layouts/", include("django_bi.layout.urls", namespace="layout")),
]
```

### Generating new dashboards

1. Create or update models inside `apps.*` or `django_bi`.
2. Generate migrations for the updated models:

   ```bash
   python manage.py makemigrations apps.accounts apps.production django_bi
   ```

3. Apply the migrations and reload the server:

   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

Your changes will be reflected in the dashboards after the server restarts.

## Contributing

1. Fork the repository and create a new branch for your feature or fix.
2. Make your changes along with tests or documentation updates.
3. Run the test suite and ensure `npm run build` completes without errors.
4. Submit a pull request describing your changes.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for
details.
