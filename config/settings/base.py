"""Base settings for manufacturing management system."""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-manufacturing-system-default-key-2026')
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')

# Hosts & Security
allowed_hosts_env = os.getenv('ALLOWED_HOSTS', '')
if allowed_hosts_env:
    ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_env.split(',') if host.strip()]
    for default_h in ('.vercel.app', '.now.sh', 'localhost', '127.0.0.1'):
        if default_h not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(default_h)
else:
    ALLOWED_HOSTS = ['*', '.vercel.app', '.now.sh', 'localhost', '127.0.0.1']

# CSRF Trusted Origins (Essential for Vercel HTTPS & custom domains)
csrf_trusted_env = os.getenv('CSRF_TRUSTED_ORIGINS', '')
if csrf_trusted_env:
    CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in csrf_trusted_env.split(',') if origin.strip()]
    if 'https://*.vercel.app' not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append('https://*.vercel.app')
else:
    CSRF_TRUSTED_ORIGINS = [
        'https://*.vercel.app',
        'https://*.now.sh',
        'http://localhost:8000',
        'http://127.0.0.1:8000',
    ]


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    
    # Third-party
    'rest_framework',
    
    # Internal apps
    'apps.accounts.apps.AccountsConfig',
    'apps.permissions.apps.PermissionsConfig',
    'apps.products.apps.ProductsConfig',
    'apps.production.apps.ProductionConfig',
    'apps.quality.apps.QualityConfig',
    'apps.dispatch.apps.DispatchConfig',
    'apps.documents.apps.DocumentsConfig',
    'apps.reports.apps.ReportsConfig',
    'apps.notifications.apps.NotificationsConfig',
    'apps.audit.apps.AuditConfig',
    
    # Panel apps
    'admin_panel.apps.AdminPanelConfig',
    'user_panel.apps.UserPanelConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.accounts.middleware.UserStatusCheckMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',
            BASE_DIR / 'admin_panel' / 'templates',
            BASE_DIR / 'user_panel' / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.notifications.context_processors.notifications_processor',
                'apps.permissions.context_processors.permissions_processor',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Database
DATABASE_URL = os.getenv('DATABASE_URL')
USE_POSTGRES = os.getenv('USE_POSTGRES', 'False').lower() in ('true', '1', 'yes')

if DATABASE_URL:
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
elif USE_POSTGRES:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'manufacturing_db'),
            'USER': os.getenv('DB_USER', 'postgres'),
            'PASSWORD': os.getenv('DB_PASSWORD', 'postgres'),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
        }
    }
else:
    # On Vercel without a configured database, fallback to /tmp to prevent read-only filesystem crash
    sqlite_db_path = Path('/tmp/db.sqlite3') if os.getenv('VERCEL') else BASE_DIR / 'db.sqlite3'
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': sqlite_db_path,
        }
    }

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 6},
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
    BASE_DIR / 'admin_panel' / 'static',
    BASE_DIR / 'user_panel' / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise storage: compress and cache static files
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = Path('/tmp/media') if os.getenv('VERCEL') else BASE_DIR / 'media'


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard-redirect/'
LOGOUT_REDIRECT_URL = '/login/'

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
}

# Max upload size: 25MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 26214400
FILE_UPLOAD_MAX_MEMORY_SIZE = 26214400

# Logging: Stream errors to stdout/stderr for Vercel Runtime Logs
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '[%(asctime)s] %(levelname)s %(name)s: %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

