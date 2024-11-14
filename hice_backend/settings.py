from dotenv import load_dotenv
import os
import sys
from pathlib import Path
import boto3

load_dotenv()

AWS_CLOUDWATCH_LOGGER_ACCESS_KEY = os.getenv("AWS_CLOUDWATCH_LOGGER_ACCESS_KEY")
AWS_CLOUDWATCH_LOGGER_SECRET_KEY = os.getenv("AWS_CLOUDWATCH_LOGGER_SECRET_KEY")
AWS_CLOUDWATCH_LOGGER_REGION_NAME = os.getenv("AWS_CLOUDWATCH_LOGGER_REGION_NAME")

boto3_logs_client = boto3.client(
    "logs",
    region_name=AWS_CLOUDWATCH_LOGGER_REGION_NAME,
    aws_access_key_id=AWS_CLOUDWATCH_LOGGER_ACCESS_KEY,
    aws_secret_access_key=AWS_CLOUDWATCH_LOGGER_SECRET_KEY,
)
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")

ENVIRONMENT = os.getenv("DJANGO_ENV")
if not ENVIRONMENT:
    ENVIRONMENT = "production"

DEBUG = ENVIRONMENT == "development"

ALLOWED_HOSTS = [
    "127.0.0.1",
    "hice-backend.us-west-2.elasticbeanstalk.com",
    "api.edukona.com",
    "localhost",
]

INSTALLED_APPS = [
    "channels_redis",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "api",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "drf_spectacular",
    "channels",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "hice_backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "hice_backend.wsgi.application"
ASGI_APPLICATION = "hice_backend.asgi.application"

# CHANNEL_LAYERS = {
#     "default": {
#         "BACKEND": "channels_redis.core.RedisChannelLayer",
#         "CONFIG": {
#             "hosts": [("localhost", 6379)],
#         },
#     },
# }

if DEBUG:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        },
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [(os.getenv("REDIS"), 6379)],  # Use your Redis endpoint and port
            },
        },
    }

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

# run sqlite if test is in the argument

# Detect if pytest is running
TESTING = False
if "pytest" in sys.modules or "pytest" in sys.argv[0]:
    TESTING = True

if TESTING or "test" in sys.argv:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",  # Use in-memory SQLite database for faster tests
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql_psycopg2",
            "NAME": os.getenv("DB_NAME"),
            "USER": os.getenv("DB_USER"),
            "PASSWORD": os.getenv("DB_PASS"),
            "HOST": os.getenv("DB_HOST"),
            "PORT": "",
        }
    }

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOW_ALL_ORIGINS = True  # Disable allowing all origins
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # Allow your local development environment
    "https://edukona.com",  # Allow your production frontend domain
]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
    ],
}

logging_level = "INFO" if ENVIRONMENT == "production" else "DEBUG"
handlers = ["console", "file"]
if ENVIRONMENT == "production" and TESTING is False:
    handlers.append("watchtower")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",  # if DEBUG logs are needed look at the debug.log file
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": os.path.join(BASE_DIR, "debug.log"),
            "formatter": "verbose",
        },
        "watchtower": {
            "class": "watchtower.CloudWatchLogHandler",
            "boto3_client": boto3_logs_client,
            "log_group": f"app-{ENVIRONMENT}",
            "level": "INFO",
        },
    },
    "loggers": {
        "django": {
            "handlers": handlers,
            "level": logging_level,
            "propagate": True,
        },
        "channels": {
            "handlers": handlers,
            "level": logging_level,
            "propagate": True,
        },
        "api.consumers": {
            "handlers": handlers,
            "level": logging_level,
            "propagate": True,
        },
    },
}

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", default="us-east-1")
AWS_ROLE_ARN = os.getenv("AWS_ROLE_ARN")

AWS_LAMBDA_INVOKER_ACCESS_KEY_ID = os.getenv("AWS_LAMBDA_INVOKER_ACCESS_KEY_ID")
AWS_LAMBDA_INVOKER_SECRET_ACCESS_KEY = os.getenv("AWS_LAMBDA_INVOKER_SECRET_ACCESS_KEY")
AWS_LAMBDA_INVOKER_REGION_NAME = os.getenv("AWS_LAMBDA_INVOKER_REGION_NAME", default="us-east-1")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
