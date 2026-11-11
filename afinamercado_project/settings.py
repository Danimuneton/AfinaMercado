"""
Configuración de Django - AfinaMercado.

Todo lo sensible o dependiente del entorno (secretos, hosts, URLs de los
microservicios, broker) se lee de variables de entorno, para poder desplegar
la misma imagen en local y en AWS EC2.
"""

import os
from pathlib import Path

from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent


def _env_bool(nombre, defecto=False):
    return os.environ.get(nombre, str(defecto)).lower() in ("1", "true", "yes", "si")


def _env_lista(nombre, defecto=""):
    return [v.strip() for v in os.environ.get(nombre, defecto).split(",") if v.strip()]


# ---------------------------------------------------------------------------
# Seguridad
# ---------------------------------------------------------------------------
DEBUG = _env_bool("DJANGO_DEBUG", True)

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError("DJANGO_SECRET_KEY es obligatoria cuando DJANGO_DEBUG=False")
    SECRET_KEY = "django-insecure-solo-para-desarrollo-local"

ALLOWED_HOSTS = _env_lista("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = _env_lista("DJANGO_CSRF_TRUSTED_ORIGINS")

# Nginx termina la conexión y reenvía la petición a Django (conserva Host con puerto).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True


# ---------------------------------------------------------------------------
# Aplicaciones
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "rest_framework",
    "ordenes",  # API legacy v1 (monolito)
    "web",      # Interfaz de usuario (consume los microservicios v2)
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "afinamercado_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "web.context_processors.carrito",
            ],
        },
    },
]

WSGI_APPLICATION = "afinamercado_project.wsgi.application"


# ---------------------------------------------------------------------------
# Base de datos (PostgreSQL en Docker, SQLite en local)
# ---------------------------------------------------------------------------
if os.environ.get("DB_ENGINE") == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME", "afinamercado"),
            "USER": os.environ.get("DB_USER", "afinamercado"),
            "PASSWORD": os.environ.get("DB_PASSWORD", "afinamercado"),
            "HOST": os.environ.get("DB_HOST", "db"),
            "PORT": os.environ.get("DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# El proyecto se creó con Django 6 (BigAutoField por defecto). Se fija para que
# las migraciones existentes coincidan también con Django 5.2 LTS.
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------------
# Autenticación
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "web:login"
LOGIN_REDIRECT_URL = "web:catalogo"
LOGOUT_REDIRECT_URL = "web:catalogo"


# ---------------------------------------------------------------------------
# Internacionalización (i18n con gettext)
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "es"
LANGUAGES = [
    ("es", _("Español")),
    ("en", _("Inglés")),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Archivos estáticos (servidos por WhiteNoise detrás de Nginx)
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}


# ---------------------------------------------------------------------------
# Caché (tasas de cambio del Adapter de divisas)
# ---------------------------------------------------------------------------
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


# ---------------------------------------------------------------------------
# Microservicios (Strangler Pattern) - comunicación interna por la red de Docker
# ---------------------------------------------------------------------------
SERVICE_TOKEN = os.environ.get("SERVICE_TOKEN", "token-solo-desarrollo")
MICROSERVICIOS = {
    "catalogo": os.environ.get("CATALOGO_URL", "http://flask_catalogo_service:5000"),
    "carrito": os.environ.get("CARRITO_URL", "http://flask_carrito_service:5000"),
    "ordenes": os.environ.get("ORDENES_URL", "http://flask_ordenes_service:5000"),
    "pagos": os.environ.get("PAGO_URL", "http://flask_pago_service:5000"),
}
MICROSERVICIOS_TIMEOUT = float(os.environ.get("MICROSERVICIOS_TIMEOUT", "8"))


# ---------------------------------------------------------------------------
# Integraciones externas
# ---------------------------------------------------------------------------
# API de terceros (tasas de cambio) consumida mediante el patrón Adapter.
DIVISAS_PROVEEDOR = os.environ.get("DIVISAS_PROVEEDOR", "exchangerate_api")  # o "tasa_fija"
DIVISAS_API_URL = os.environ.get("DIVISAS_API_URL", "https://open.er-api.com/v6/latest")
DIVISAS_TASA_FIJA_USD = os.environ.get("DIVISAS_TASA_FIJA_USD", "0.00025")
DIVISAS_CACHE_SEGUNDOS = int(os.environ.get("DIVISAS_CACHE_SEGUNDOS", "3600"))

# Servicio del equipo aliado (se configura cuando el profesor asigne el equipo).
ALIADO_NOMBRE = os.environ.get("ALIADO_NOMBRE", "")
ALIADO_API_URL = os.environ.get("ALIADO_API_URL", "")
ALIADO_TIMEOUT = float(os.environ.get("ALIADO_TIMEOUT", "6"))


# ---------------------------------------------------------------------------
# Celery (Message Broker: Redis)
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/1")


# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO")},
}
