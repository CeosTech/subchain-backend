"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/wsgi/
"""

import os
from pathlib import Path

import django
from django.core.wsgi import get_wsgi_application


def _collectstatic_if_requested():
    """
    Render (plan gratuit) n'autorise pas toujours une commande build dédiée.
    Quand la variable AUTO_COLLECTSTATIC est positionnée, on exécute collectstatic
    au démarrage du worker, ce qui revient à "préparer" staticfiles avant que
    WhiteNoise ne commence à les servir.
    """
    auto_collect = os.getenv("AUTO_COLLECTSTATIC", "").strip().lower()
    if auto_collect not in ("1", "true", "yes"):
        return

    from django.conf import settings
    from django.core.management import call_command
    from django.core.management.base import CommandError

    sentinel = Path(settings.STATIC_ROOT) / ".render_static_ready"
    if sentinel.exists():
        return

    try:
        call_command("collectstatic", interactive=False, verbosity=0)
    except CommandError as exc:
        print(f"[collectstatic] skipped ({exc})")
    else:
        sentinel.write_text("ok", encoding="utf-8")
        print("[collectstatic] static assets collected at startup")


def _migrate_if_requested():
    """
    Même contrainte Render : pas de commande `python manage.py migrate`.
    On permet donc d'exécuter les migrations au boot si AUTO_MIGRATE est défini.
    """
    auto_migrate = os.getenv("AUTO_MIGRATE", "").strip().lower()
    if auto_migrate not in ("1", "true", "yes"):
        return

    from django.core.management import call_command

    try:
        call_command("migrate", interactive=False, verbosity=1)
    except Exception as exc:  # pragma: no cover - log best effort
        print(f"[migrate] failed at startup: {exc}")
    else:
        print("[migrate] database up to date at startup")


def _create_superuser_if_requested():
    """
    Permet de créer un superuser sans shell Render.
    Requiert AUTO_CREATE_SUPERUSER=true + DJANGO_SUPERUSER_EMAIL/PASSWORD/WALLET_ADDRESS.
    """
    auto_flag = os.getenv("AUTO_CREATE_SUPERUSER", "").strip().lower()
    if auto_flag not in ("1", "true", "yes"):
        return

    email = os.getenv("DJANGO_SUPERUSER_EMAIL", "").strip()
    password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "").strip()
    wallet = os.getenv("DJANGO_SUPERUSER_WALLET_ADDRESS", "").strip()
    username = os.getenv("DJANGO_SUPERUSER_USERNAME", "").strip() or (email.split("@")[0] if email else "")

    if not email or not password or not wallet:
        print("[superuser] missing DJANGO_SUPERUSER_EMAIL/PASSWORD/WALLET_ADDRESS")
        return

    from django.contrib.auth import get_user_model

    User = get_user_model()
    if User.objects.filter(email=email).exists():
        print("[superuser] account already exists, skipping creation")
        return

    try:
        User.objects.create_superuser(
            email=email,
            password=password,
            username=username or email,
            wallet_address=wallet,
        )
    except Exception as exc:  # pragma: no cover - defensive
        print(f"[superuser] failed to create: {exc}")
    else:
        print(f"[superuser] created admin user {email}")


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
_migrate_if_requested()
_create_superuser_if_requested()
_collectstatic_if_requested()

application = get_wsgi_application()
