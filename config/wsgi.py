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


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
_migrate_if_requested()
_collectstatic_if_requested()

application = get_wsgi_application()
