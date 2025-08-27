from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "test"
ALLOWED_HOSTS = []

INSTALLED_APPS = [
    "apps.common",
    "apps.blocks",
    "apps.production",
    "apps.workflow",
    "apps.accounts",
    "apps.permissions",
    "django.contrib.auth",
    "django.contrib.contenttypes",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

MIDDLEWARE = []
ROOT_URLCONF = "apps.blocks.urls"
TEMPLATES = []
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.CustomUser"
