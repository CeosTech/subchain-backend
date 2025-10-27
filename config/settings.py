import os
from pathlib import Path
from datetime import timedelta

# 📁 BASE DIR
BASE_DIR = Path(__file__).resolve().parent.parent

# 🔐 SÉCURITÉ
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key")
DEBUG = True
ALLOWED_HOSTS = ["*"]

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

# 🗄️ DATABASE (par défaut SQLite, pour dev)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
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
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# 🌐 CORS
CORS_ALLOW_ALL_ORIGINS = True

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
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "no-reply@subchain.ai"
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
