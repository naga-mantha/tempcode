from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "test"
ALLOWED_HOSTS = []

INSTALLED_APPS = []

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

MIDDLEWARE = []
ROOT_URLCONF = "mag360.test_urls"
TEMPLATES = []
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
