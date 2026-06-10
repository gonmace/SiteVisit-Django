import os
from decouple import config, Csv

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(PROJECT_DIR)

_SECRET_KEY_DEFAULT = 'django-insecure-default-only-for-dev-run-make-setup'
SECRET_KEY = config('SECRET_KEY', default=_SECRET_KEY_DEFAULT)

DEBUG = config('DEBUG', default=False, cast=bool)

# Validar solo cuando existe .env (entorno configurado) pero SECRET_KEY no fue definido.
# Sin .env = instalación inicial, el default es aceptable.
if SECRET_KEY == _SECRET_KEY_DEFAULT and os.path.exists(os.path.join(BASE_DIR, '.env')):
    raise ValueError("SECRET_KEY no está en .env. Ejecuta 'make setup' para generarlo.")

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='', cast=Csv())

ADMIN_URL = config('ADMIN_URL', default='admin/')

# Application definition

INSTALLED_APPS = [
    'home',
    'axes',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    'django.contrib.humanize',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'csp.middleware.CSPMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'axes.middleware.AxesMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

INSTALLED_APPS += ['tailwind', 'theme']
TAILWIND_APP_NAME = 'theme'

if DEBUG:
    INSTALLED_APPS += ['django_browser_reload']
    MIDDLEWARE += ['django_browser_reload.middleware.BrowserReloadMiddleware']
    INTERNAL_IPS = ['127.0.0.1', '::1']
    import sys
    if sys.platform == 'win32':
        NPM_BIN_PATH = r'C:\Users\gonma\AppData\Roaming\fnm\node-versions\v24.15.0\installation\npm.cmd'

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'home.context_processors.theme',
                'visits.context_processors.pending_visits_count',
                'users.context_processors.pending_technicians_count',
                'notifications.context_processors.notifications_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# Database: SQLite por defecto en dev, PostgreSQL si se define POSTGRES_DB
if config('POSTGRES_DB', default=''):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('POSTGRES_DB'),
            'USER': config('POSTGRES_USER'),
            'PASSWORD': config('POSTGRES_PASSWORD'),
            'HOST': config('POSTGRES_HOST', default='postgres'),
            'PORT': config('POSTGRES_PORT', default='5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/La_Paz'
USE_I18N = True
USE_TZ = True

# Django 6.0 eliminó USE_L10N; la localización siempre está activa.
# FORMAT_MODULE_PATH sobreescribe el formato del locale 'es' para usar
# punto como separador decimal y coma como separador de miles.
FORMAT_MODULE_PATH = ['core.formats']
DECIMAL_SEPARATOR = '.'
THOUSAND_SEPARATOR = ','
NUMBER_GROUPING = 3
USE_THOUSAND_SEPARATOR = False  # usar |intcomma explícito en templates

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
WHITENOISE_MANIFEST_STRICT = not DEBUG  # True en prod: rechaza archivos sin entrada en manifest

STORAGES = {
    'staticfiles': {
        # CompressedManifestStaticFilesStorage: hashes en filenames (cache-busting seguro)
        # + archivos .gz pre-generados que nginx sirve con gzip_static on
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email: consola en dev, SMTP en prod si se configura EMAIL_HOST
if config('EMAIL_HOST', default=''):
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = config('EMAIL_HOST')
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
    EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
    DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@example.com')
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ── Seguridad ──────────────────────────────────────────────────────────────────
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_TRUSTED_ORIGINS = [o for o in config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv()) if o]
if DEBUG:
    _port = config('APP_PORT', default='8000')
    for _origin in [f'http://localhost:{_port}', f'http://127.0.0.1:{_port}']:
        if _origin not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(_origin)

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

X_FRAME_OPTIONS = 'DENY'

# ── Redis (cache, sesiones) ───────────────────────────────────────────────────
# En dev sin .env, se conecta a localhost:6379 (Docker Desktop expone el puerto al host).
# En producción, .env siempre define REDIS_URL=redis://redis:6379/0 (nombre del servicio Docker).
REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
    }
}

# En DEBUG las sesiones van a la BD (alineado con Axes en dev): el login en /manager/
# no se “pierde” si Redis está caído o REDIS_URL no coincide con el puerto del contenedor.
if DEBUG:
    SESSION_ENGINE = 'django.contrib.sessions.backends.db'
else:
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'

# ── django-axes (protección brute force) ──────────────────────────────────────
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # hora
AXES_LOCKOUT_PARAMETERS = ['ip_address', 'username']

if DEBUG:
    # En desarrollo se usa el handler de base de datos para no depender de Redis.
    # Permite correr 'python manage.py runserver' sin contenedores activos.
    AXES_HANDLER = 'axes.handlers.database.AxesDatabaseHandler'
else:
    # En producción Redis siempre está disponible — más rápido bajo ataques.
    AXES_HANDLER = 'axes.handlers.cache.AxesCacheHandler'
    AXES_CACHE = 'default'

# ── Content Security Policy ───────────────────────────────────────────────────
# Scripts: CDN (Leaflet, Chart.js, FA, Toasty) + inline (templates usan <script> inline)
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC  = ("'self'", "cdn.jsdelivr.net", "'unsafe-inline'")
# Estilos: CDN + Google Fonts + inline (Leaflet inyecta style= en marcadores)
CSP_STYLE_SRC   = ("'self'", "cdn.jsdelivr.net", "fonts.googleapis.com", "'unsafe-inline'")
# Imágenes: mapa OSM (Leaflet rota a/b/c.tile.openstreetmap.org)
CSP_IMG_SRC     = ("'self'", "data:", "https://*.tile.openstreetmap.org")
# Fuentes: Font Awesome (jsdelivr) + Google Fonts (gstatic)
CSP_FONT_SRC    = ("'self'", "cdn.jsdelivr.net", "fonts.gstatic.com")
# Fetch/XHR: solo mismo origen (APIs internas) + websockets en dev
if DEBUG:
    CSP_CONNECT_SRC = ("'self'", "ws://localhost:*", "ws://127.0.0.1:*")
else:
    CSP_CONNECT_SRC = ("'self'",)

# ── Integración n8n (no utilizado por el momento) ────────────────────────────
# N8N_URL = config('N8N_URL', default='')
# N8N_API_KEY = config('N8N_API_KEY', default='')
# N8N_WEBHOOK_URL = config('N8N_WEBHOOK_URL', default='')

# ── Admins y logging ──────────────────────────────────────────────────────────
ADMINS = [('Admin', 'admin@example.com')]
MANAGERS = ADMINS

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {'()': 'django.utils.log.RequireDebugFalse'}
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}

# ── SiteVisit additions ───────────────────────────────────────────────────────
from datetime import timedelta

AUTH_USER_MODEL = 'users.User'

INSTALLED_APPS += [
    'users',
    'sites',
    'visits',
    'photos',
    'dashboard',
    'notifications',
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'import_export',
]

MIDDLEWARE.insert(1, 'corsheaders.middleware.CorsMiddleware')

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',
    'ALLOWED_VERSIONS': ['v1'],
    'DEFAULT_VERSION': 'v1',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'login': '5/min',
        'activation': '10/hour',
    },
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_CLAIM': 'user_id',
    'UPDATE_LAST_LOGIN': True,
}

CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='', cast=Csv())

LOGIN_REDIRECT_URL = '/manager/'

# ── Web Push (VAPID) ──────────────────────────────────────────────────────────
# Claves generadas una sola vez (make setup / scripts/generate_vapid.py).
# NUNCA regenerarlas en producción: invalida todas las suscripciones existentes.
VAPID_PUBLIC_KEY  = config('VAPID_PUBLIC_KEY', default='')
VAPID_PRIVATE_KEY = config('VAPID_PRIVATE_KEY', default='')
VAPID_ADMIN_EMAIL = config('VAPID_ADMIN_EMAIL', default='admin@example.com')
