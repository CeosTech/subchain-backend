from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Integration, IntegrationStatus


class IntegrationModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="integrations@example.com",
            password="pass1234",
        )

    def test_mark_success_updates_fields(self):
        integration = Integration.objects.create(user=self.user, name="Webhook", endpoint_url="https://example.com")

        integration.mark_success()

        integration.refresh_from_db()
        self.assertEqual(integration.status, IntegrationStatus.HEALTHY)
        self.assertEqual(integration.failure_count, 0)
        self.assertEqual(integration.last_error_message, "")

    def test_mark_failure_escalates_status(self):
        integration = Integration.objects.create(user=self.user, name="Discord", endpoint_url="https://discord.com")

        integration.mark_failure("Timeout")
        integration.refresh_from_db()
        self.assertEqual(integration.status, IntegrationStatus.DEGRADED)

        integration.mark_failure("Timeout 2")
        integration.mark_failure("Timeout 3")
        integration.refresh_from_db()
        self.assertEqual(integration.status, IntegrationStatus.FAILED)
        self.assertGreater(integration.failure_count, 0)
