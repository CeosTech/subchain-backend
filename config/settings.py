import os
from pathlib import Path
from datetime import timedelta
from django.core.exceptions import ImproperlyConfigured

# 📁 BASE DIR
BASE_DIR = Path(__file__).resolve().parent.parent

# 🔐 SÉCURITÉ
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key")
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() == "true"
allowed_hosts_env = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_env.split(",") if host.strip()]

# 🧩 APPS
INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # 3rd Party
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "rest_framework_simplejwt",
    "corsheaders",
    "drf_yasg",

    # Local apps
    "accounts",
    "subscriptions",
    "payments",
    "algorand",
    "currency",
    "webhooks",
    "analytics",
    "notifications",
    "integrations",
]

# 🧱 MIDDLEWARE
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "integrations.middleware.x402.X402PaymentMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# 🔗 URL + WSGI
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"


# 📦 TEMPLATES
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

# 🗄️ DATABASE (SQLite par défaut, Postgres via DATABASE_URL)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    from urllib.parse import urlparse

    parsed_db_url = urlparse(DATABASE_URL)
    if parsed_db_url.scheme not in ("postgres", "postgresql"):
        raise ImproperlyConfigured("Unsupported database scheme in DATABASE_URL")

    DATABASES["default"] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed_db_url.path.lstrip("/"),
        "USER": parsed_db_url.username,
        "PASSWORD": parsed_db_url.password,
        "HOST": parsed_db_url.hostname,
        "PORT": parsed_db_url.port or "",
    }

# 👤 USER MODEL
AUTH_USER_MODEL = "accounts.User"

# 🔐 MOTS DE PASSE
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

# 🌍 LOCALISATION
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# 📁 STATIC & MEDIA
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# 🌐 CORS
CORS_ALLOW_ALL_ORIGINS = DEBUG
if not DEBUG:
    allowed_origins = os.getenv("CORS_ALLOWED_ORIGINS", "")
    CORS_ALLOWED_ORIGINS = [
        origin.strip() for origin in allowed_origins.split(",") if origin.strip()
    ]

# 🔑 JWT AUTH
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
}

# 📧 EMAIL
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@subchain.ai")
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")

# 📚 SWAGGER
SWAGGER_SETTINGS = {
    "USE_SESSION_AUTH": False,
    "SECURITY_DEFINITIONS": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
        }
    },
}

# 💰 CONFIG FINANCIÈRE
SUBCHAIN_TREASURY_WALLET_ADDRESS = os.getenv("SUBCHAIN_TREASURY_WALLET_ADDRESS", "TREASURY_WALLET")
PLATFORM_FEE_WALLET_ADDRESS = os.getenv("PLATFORM_FEE_WALLET_ADDRESS", "PLATFORM_WALLET")
PLATFORM_FEE_PERCENT = float(os.getenv("PLATFORM_FEE_PERCENT", 5.0))  # 5% par défaut

# 🪙 ALGORAND
ALGO_NODE_URL = os.getenv("ALGO_NODE_URL", "https://testnet-api.algonode.cloud")
ALGO_INDEXER_URL = os.getenv("ALGO_INDEXER_URL", "https://testnet-idx.algonode.cloud")
ALGO_API_TOKEN = os.getenv("ALGO_API_TOKEN", "")  # Si nécessaire (souvent vide avec Algonode)
TINYMAN_SWAP_SLIPPAGE = float(os.getenv("TINYMAN_SWAP_SLIPPAGE", 0.03))  # 3% max slippage
ALGORAND_NETWORK = os.getenv("ALGORAND_NETWORK", "testnet")
ALGORAND_ACCOUNT_ADDRESS = os.getenv("ALGORAND_ACCOUNT_ADDRESS", "")
ALGORAND_ACCOUNT_MNEMONIC = os.getenv("ALGORAND_ACCOUNT_MNEMONIC", "")
ALGORAND_USDC_ASSET_ID_MAINNET = int(os.getenv("ALGORAND_USDC_ASSET_ID_MAINNET", 31566704))
ALGORAND_USDC_ASSET_ID_TESTNET = int(os.getenv("ALGORAND_USDC_ASSET_ID_TESTNET", 10458941))
ALGORAND_SWAP_MAX_RETRIES = int(os.getenv("ALGORAND_SWAP_MAX_RETRIES", 3))
ALGORAND_SWAP_WAIT_ROUNDS = int(os.getenv("ALGORAND_SWAP_WAIT_ROUNDS", 4))
ALGORAND_SWAP_RETRY_DELAY_SECONDS = float(os.getenv("ALGORAND_SWAP_RETRY_DELAY_SECONDS", 1.5))

# 🧾 x402 micropayments
X402_ENABLED = os.getenv("X402_ENABLED", "false").lower() == "true"
X402_PAYTO_ADDRESS = os.getenv("X402_PAYTO_ADDRESS", "")
X402_DEFAULT_PRICE = os.getenv("X402_DEFAULT_PRICE", "0")
X402_PRICING_RULES = os.getenv("X402_PRICING_RULES", "{}")
X402_CALLBACK_URL = os.getenv("X402_CALLBACK_URL", "")
X402_NONCE_TTL_SECONDS = int(os.getenv("X402_NONCE_TTL_SECONDS", 300))
X402_CURRENCY = os.getenv("X402_CURRENCY", "USDC")
X402_NETWORK = os.getenv("X402_NETWORK", "algorand")
X402_RECEIPT_VERIFIER = os.getenv("X402_RECEIPT_VERIFIER", "")
X402_CACHE_ALIAS = os.getenv("X402_CACHE_ALIAS", "default")
_x402_asset_id = os.getenv("X402_ASSET_ID", "")
X402_ASSET_ID = int(_x402_asset_id) if _x402_asset_id else None
X402_ASSET_DECIMALS = int(os.getenv("X402_ASSET_DECIMALS", 6))

# Celery
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ALWAYS_EAGER = os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true"

# ✅ LOGS
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
