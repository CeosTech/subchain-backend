from decimal import Decimal

from django.core.management.base import BaseCommand

from subscriptions.models import Plan, PlanFeature, PlanInterval


class Command(BaseCommand):
    help = "Seed default subscription plans and features."

    PLANS = [
        {
            "code": "starter",
            "name": "Starter",
            "description": "Perfect for beginners with limited needs",
            "amount": Decimal("0"),
            "currency": "ALGO",
            "interval": PlanInterval.MONTH,
            "trial_days": 14,
            "features": [
                "Basic API Access",
                "Email Support",
                "1 Project",
            ],
        },
        {
            "code": "pro",
            "name": "Pro",
            "description": "For growing businesses and builders",
            "amount": Decimal("9.990000"),
            "currency": "ALGO",
            "interval": PlanInterval.MONTH,
            "trial_days": 7,
            "features": [
                "Unlimited Projects",
                "Priority Email Support",
                "Analytics Dashboard",
            ],
        },
        {
            "code": "enterprise",
            "name": "Enterprise",
            "description": "Advanced features and custom support",
            "amount": Decimal("49.990000"),
            "currency": "ALGO",
            "interval": PlanInterval.MONTH,
            "trial_days": 0,
            "features": [
                "Custom SLAs",
                "Dedicated Support",
                "Webhook Logs",
                "Custom Integrations",
            ],
        },
    ]

    def handle(self, *args, **options):
        for payload in self.PLANS:
            features = payload.pop("features", [])
            plan, created = Plan.objects.get_or_create(
                code=payload["code"],
                defaults=payload,
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created plan: {plan.code}"))
            else:
                self.stdout.write(self.style.WARNING(f"Plan already exists: {plan.code}"))

            for order, name in enumerate(features):
                PlanFeature.objects.get_or_create(
                    plan=plan,
                    name=name,
                    defaults={"sort_order": order},
                )
