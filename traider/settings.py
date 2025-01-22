import os
from pathlib import Path

APP_NAME = "TRAIDER"

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = bool(int(os.environ.get(f"{APP_NAME}_DEBUG", 1)))

SECRET_KEY = os.environ.get(f"{APP_NAME}_SECRET_KEY", "djangosecretkey12345fivefivefaa")

ALLOWED_HOSTS = os.environ.get(f"{APP_NAME}_HOSTS", "localhost 127.0.0.1").split()


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_plotly_dash.apps.DjangoPlotlyDashConfig",
    "app",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_plotly_dash.middleware.ExternalRedirectionMiddleware",
]

ROOT_URLCONF = "traider.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "traider/templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "traider.wsgi.application"


# Database

if os.environ.get(f"{APP_NAME}_DB", None):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql_psycopg2",
            "NAME": os.environ.get(f"{APP_NAME}_DB"),
            "USER": os.environ.get(f"{APP_NAME}_DB_USER"),
            "PASSWORD": os.environ.get(f"{APP_NAME}_DB_PASSWORD"),
            "HOST": os.environ.get(f"{APP_NAME}_DB_HOST"),
            "PORT": "5432",
        },
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization

LANGUAGE_CODE = "en-us"

TIME_ZONE = "America/Chicago"

USE_I18N = True

USE_TZ = True

USE_L10N = True


# Static files (CSS, JavaScript, Images)

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "static"
STATICFILES_DIRS = [
    (BASE_DIR / "staticfiles"),
]
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "django_plotly_dash.finders.DashAssetFinder",
    "django_plotly_dash.finders.DashComponentFinder",
    "django_plotly_dash.finders.DashAppDirectoryFinder",
]

MEDIA_URL = "/media/"
MEDIA_ROOT = os.environ.get(f"{APP_NAME}_MEDIA_ROOT", BASE_DIR / "media")


# Default primary key field type

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SECURE_CROSS_ORIGIN_OPENER_POLICY = None


# Authentication

LOGIN_URL = "index"
LOGIN_REDIRECT_URL = "index"


# Logging settings

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "formatters": {
        "django.server": {
            "()": "django.utils.log.ServerFormatter",
            "format": "[%(server_time)s] %(message)s",
        }
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "filters": ["require_debug_true"],
            "class": "logging.StreamHandler",
        },
        "console_on_not_debug": {
            "level": "WARNING",
            "filters": ["require_debug_false"],
            "class": "logging.StreamHandler",
        },
        "django.server": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "django.server",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "console_on_not_debug"],
            "level": "INFO",
        },
        "django.server": {
            "handlers": ["django.server"],
            "level": "INFO",
            "propagate": False,
        },
    },
}


# Broker settings

CELERY_BROKER_URL = os.environ.get(
    f"{APP_NAME}_CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//"
)


# API Keys

OANDA_API = os.environ.get(f"{APP_NAME}_OANDA_DEMO_API")
OANDA_SECRET = os.environ.get(f"{APP_NAME}_OANDA_DEMO_SECRET")
OANDA_BASE_URL = os.environ.get(
    f"{APP_NAME}_OANDA_BASE_URL", "https://api-fxpractice.oanda.com/v3/"
)

# Other

X_FRAME_OPTIONS = "SAMEORIGIN"
PLOTLY_COMPONENTS = ["dpd_components"]
DATA_UPLOAD_MAX_MEMORY_SIZE = 50000000
