from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from algorand.contracts.subscription_contract import SubscriptionContractConfig
from algorand.utils import deploy_subscription_contract
from subscriptions.models import Plan


class Command(BaseCommand):
    help = "Deploy Algorand subscription contracts for plans without an app ID"

    def add_arguments(self, parser):
        parser.add_argument("plan_codes", nargs="*", help="Plan codes to deploy. Deploys all without app if omitted.")

    def handle(self, *args, **options):
        plan_codes = options["plan_codes"]
        plans = Plan.objects.filter(contract_app_id__isnull=True)
        if plan_codes:
            plans = plans.filter(code__in=plan_codes)

        if not plans.exists():
            raise CommandError("No plans found that require deployment.")

        deployed = 0
        for plan in plans:
            cfg = SubscriptionContractConfig(
                plan_id=plan.id,
                price_micro_algo=int(plan.amount * 1_000_000),
                renew_interval_rounds=30 * 60,  # approx 30 days (rough placeholder)
                treasury_address=settings.ALGORAND_ACCOUNT_ADDRESS,
            )
            app_id = deploy_subscription_contract(cfg)
            plan.contract_app_id = app_id
            plan.save(update_fields=["contract_app_id"])
            deployed += 1
            self.stdout.write(self.style.SUCCESS(f"Deployed contract for plan {plan.code} -> app {app_id}"))

        self.stdout.write(self.style.SUCCESS(f"Deployment complete. {deployed} plan(s) updated."))
