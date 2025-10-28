from unittest import mock

from django.test import TestCase

from algorand.contracts.subscription_contract import (
    SubscriptionContractConfig,
    get_teal_sources,
)
from algorand.utils import compile_subscription_contract


class SubscriptionContractTests(TestCase):
    def setUp(self):
        self.config = SubscriptionContractConfig(
            plan_id=1,
            price_micro_algo=1_000_000,
            renew_interval_rounds=1000,
            treasury_address="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAY5HFKQ",
        )

    def test_teal_sources_generated(self):
        sources = get_teal_sources(self.config)
        self.assertIn("plan_id", sources["approval"])
        self.assertTrue(sources["clear"].startswith("#pragma"))

    @mock.patch("algorand.utils.compile_teal_source")
    @mock.patch("algorand.utils.get_algod_client")
    def test_compile_subscription_contract(self, mock_client, mock_compile):
        mock_client.return_value = mock.Mock()
        mock_compile.return_value = b"compiled"
        compiled = compile_subscription_contract(self.config)
        self.assertEqual(compiled["approval"], b"compiled")
        self.assertEqual(compiled["clear"], b"compiled")
        self.assertIn("sources", compiled)
