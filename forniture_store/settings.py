import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, os.path.join(BASE_DIR, "apps"))

# Carrega variáveis do arquivo .env se ele existir
dotenv_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# --- Configurações de Segurança e Debug ---
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
DEBUG_STRING = os.environ.get("DJANGO_DEBUG", "False")
DEBUG = DEBUG_STRING.lower() in ("true", "1", "t")

## --- Configurações específicas de HTTPS ---
USE_HTTPS_SETTINGS = os.environ.get("DJANGO_USE_HTTPS_SETTINGS", "False").lower() == 'true'

if not DEBUG:
    if USE_HTTPS_SETTINGS: # Só ativa estas se estivermos explicitamente em um ambiente HTTPS
        CSRF_COOKIE_SECURE = True
        SESSION_COOKIE_SECURE = True
        SECURE_SSL_REDIRECT = True
        
        # Configurações HSTS (HTTP Strict Transport Security)
        # Use uma variável de ambiente para os segundos, padrão para 0 (desabilitado)
        SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_SECURE_HSTS_SECONDS", 31536000)) # 1 ano como padrão se HTTPS
        if SECURE_HSTS_SECONDS > 0:
            SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", "True").lower() == 'true'
            SECURE_HSTS_PRELOAD = os.environ.get("DJANGO_SECURE_HSTS_PRELOAD", "False").lower() == 'true'
    else:
        # Para produção local sem HTTPS
        CSRF_COOKIE_SECURE = False
        SESSION_COOKIE_SECURE = False
        SECURE_SSL_REDIRECT = False
        SECURE_HSTS_SECONDS = 0 # Garante que HSTS está desabilitado

    # Outras melhorias de segurança (estas são seguras para HTTP e HTTPS)
    SECURE_BROWSER_XSS_FILTER = True # Embora obsoleto na maioria dos navegadores modernos, não prejudica.
    SECURE_CONTENT_TYPE_NOSNIFF = True

if not SECRET_KEY:
    if DEBUG:
        print(
            "AVISO DE DESENVOLVIMENTO: DJANGO_SECRET_KEY não definida, usando uma chave de fallback. Defina no .env!"
        )
        SECRET_KEY = "django-insecure-p9y-*a(1fi9o#l5g2_h1k(j6=lb8jb-t%-k^u4-tdup)tl+&n7"  # Chave de fallback apenas para DEBUG
    else:
        raise ValueError(
            "ERRO CRÍTICO: DJANGO_SECRET_KEY não está definida para o ambiente de produção!"
        )

if DEBUG:
    ALLOWED_HOSTS = ["*"]  # Em debug, permite todos os hosts
else:
    allowed_hosts_env = os.environ.get("DJANGO_ALLOWED_HOSTS")
    if allowed_hosts_env:
        ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_env.split(",")]
    else:
        ALLOWED_HOSTS = []
        print(
            "AVISO CRÍTICO DE PRODUÇÃO: DJANGO_ALLOWED_HOSTS não está definida. A aplicação pode não responder a requisições ou estar insegura."
        )


# --- Configuração do Banco de Dados ---
DB_ENGINE_ENV = os.environ.get('DB_ENGINE', 'django.db.backends.postgresql')
DB_NAME_ENV = os.environ.get('DB_NAME')
DB_USER_ENV = os.environ.get('DB_USER')
DB_PASSWORD_ENV = os.environ.get('DB_PASSWORD')
DB_HOST_ENV = os.environ.get('DB_HOST', 'localhost')
DB_PORT_ENV = os.environ.get('DB_PORT', '5432')

# A lógica de verificação de DEBUG e variáveis de produção pode ser mantida ou ajustada
if not DEBUG and not all([DB_NAME_ENV, DB_USER_ENV, DB_PASSWORD_ENV, DB_HOST_ENV, DB_PORT_ENV]):
    raise ValueError(
        "ERRO CRÍTICO DE PRODUÇÃO: As variáveis de ambiente "
        "DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT não estão completamente definidas no .env."
    )
elif DEBUG and not all([DB_NAME_ENV, DB_USER_ENV, DB_PASSWORD_ENV]):
    print(
        "AVISO DE DESENVOLVIMENTO: As variáveis "
        "DB_NAME, DB_USER, ou DB_PASSWORD não estão totalmente definidas no .env. "
        "O banco de dados local pode não funcionar se não estiverem completas."
    )

DATABASES = {
    'default': {
        'ENGINE': DB_ENGINE_ENV,
        'NAME': DB_NAME_ENV,
        'USER': DB_USER_ENV,
        'PASSWORD': DB_PASSWORD_ENV,
        'HOST': DB_HOST_ENV,
        'PORT': DB_PORT_ENV,
    }
}

if not DATABASES['default'].get('NAME'):
    if not DEBUG:
        raise ValueError("ERRO CRÍTICO: Configuração do banco de dados está incompleta.")
    else:
        print(
            "AVISO DE DESENVOLVIMENTO CRÍTICO: A configuração do banco de dados 'default' está vazia. "
            "Verifique seu .env para DB_NAME, DB_USER, DB_PASSWORD."
        )

        
# --- Configurações de Aplicação ---
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    ## My Apps
    "apps.addresses",
    "apps.customers",
    "apps.docs",
    "apps.employees",
    "apps.showroom",
    # 'apps.reports',
    # 'apps.orders',
    # 'apps.products',
    # 'apps.stock',
    # 'apps.suppliers',
]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "forniture_store.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.employees.context_processors.theme_processor",
            ],
        },
    },
]

WSGI_APPLICATION = "forniture_store.wsgi.application"


# --- Configurações de Validação de Senha ---
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


# --- Configurações de Internacionalização ---
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True


# --- Configurações de Arquivos Estáticos e Mídia ---
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")  # Para 'collectstatic' em produção
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"  # Para compressão e cache busting
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),  # Para desenvolvimento
]

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")


# --- Modelo de Usuário Personalizado e URLs de Autenticação ---
AUTH_USER_MODEL = "employees.Employee"
LOGIN_URL = "/auth/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/auth/login/"


# --- Configurações de Logging ---
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        'verbose': {
            'format': '{levelname} {asctime} {name} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {name}: {message}',
            'style': '{',
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG" if DEBUG else "INFO",
            "class": "logging.StreamHandler",
            "formatter": "simple", 
        },
    },
    "loggers": {
        "django": {  # Logger raiz do Django
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
    "root": {  # Logger raiz para capturar logs não tratados por outros loggers
        "handlers": ["console"],
        "level": "DEBUG" if DEBUG else "INFO", 
    },
}

# --- Configuração de E-mail ---
if DEBUG:
    # Configurações para DESENVOLVIMENTO
    EMAIL_BACKEND = os.environ.get(
        "DJANGO_EMAIL_BACKEND_DEV", "django.core.mail.backends.console.EmailBackend"
    )
    if EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend":
        EMAIL_HOST = os.environ.get("DJANGO_EMAIL_HOST_DEV")
        EMAIL_PORT = int(os.environ.get("DJANGO_EMAIL_PORT_DEV", 587))
        EMAIL_USE_TLS = os.environ.get("DJANGO_EMAIL_USE_TLS_DEV", "True").lower() in (
            "true",
            "1",
            "t",
        )
        EMAIL_HOST_USER = os.environ.get("DJANGO_EMAIL_HOST_USER_DEV")
        EMAIL_HOST_PASSWORD = os.environ.get("DJANGO_EMAIL_HOST_PASSWORD_DEV")
        DEFAULT_FROM_EMAIL = os.environ.get(
            "DJANGO_DEFAULT_FROM_EMAIL_DEV", EMAIL_HOST_USER
        )
else:
    # Configurações para PRODUÇÃO
    EMAIL_BACKEND = os.environ.get(
        "DJANGO_EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"
    )

    if EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend":
        EMAIL_HOST = os.environ.get("DJANGO_EMAIL_HOST")
        EMAIL_PORT = int(os.environ.get("DJANGO_EMAIL_PORT", 587))
        EMAIL_USE_TLS = os.environ.get("DJANGO_EMAIL_USE_TLS", "True").lower() in (
            "true",
            "1",
            "t",
        )
        EMAIL_HOST_USER = os.environ.get("DJANGO_EMAIL_HOST_USER")
        EMAIL_HOST_PASSWORD = os.environ.get("DJANGO_EMAIL_HOST_PASSWORD")
        DEFAULT_FROM_EMAIL = os.environ.get(
            "DJANGO_DEFAULT_FROM_EMAIL", EMAIL_HOST_USER
        )

        # Verificação para garantir que as configurações de e-mail SMTP estão presentes em produção
        if not all([EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD]):
            print(
                "AVISO CRÍTICO DE PRODUÇÃO: Configurações de e-mail SMTP (HOST, USER, PASSWORD) "
                "não estão completas. O envio de e-mails pode falhar."
            )
    elif EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend":
        pass
