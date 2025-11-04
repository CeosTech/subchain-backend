import logging

from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured


logger = logging.getLogger(__name__)


class IntegrationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "integrations"

    def ready(self) -> None:
        from . import x402

        try:
            x402.initialize()
        except ImproperlyConfigured:
            raise
        except Exception:  # pragma: no cover - defensive guard during startup
            logger.exception("x402 initialization failed during app ready.")
