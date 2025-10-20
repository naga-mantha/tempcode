"""SQLite-backed settings used for test runs in CI/local development."""

from __future__ import annotations

import os

# Provide defaults so the base settings module can import without environment variables.
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ALLOWED_HOSTS", "localhost")
os.environ.setdefault("DATABASE_NAME", "test_db")
os.environ.setdefault("DATABASE_USER", "")
os.environ.setdefault("DATABASE_PASS", "")
os.environ.setdefault("DATABASE_HOST", "")
os.environ.setdefault("DATABASE_PORT", "")
os.environ.setdefault("EMAIL_HOST", "localhost")
os.environ.setdefault("EMAIL_PORT", "1025")
os.environ.setdefault("SITE_ID", "1")
os.environ.setdefault("DEFAULT_FROM_EMAIL", "noreply@example.com")
os.environ.setdefault("ADMINS", "admin@example.com")

from .settings import *  # noqa: E402,F401,F403

# Use an in-memory SQLite database for tests.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Disable migrations for project apps to speed up SQLite test setup.
PROJECT_APPS = [app for app in INSTALLED_APPS if app.startswith("apps.")]
MIGRATION_MODULES = {app.split(".", 1)[1]: None for app in PROJECT_APPS}

# Align slugification with production expectations when running unit tests.
SLUGIFY_REPLACEMENTS = [(".", "-")]
