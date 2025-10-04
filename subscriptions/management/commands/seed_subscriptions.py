from django.core.management.base import BaseCommand
from subscriptions.models import SubscriptionPlan, Feature

class Command(BaseCommand):
    help = "Seed default subscription plans and features"

    def handle(self, *args, **kwargs):
        plans = [
            {
                "name": "Starter",
                "description": "Perfect for beginners with limited needs",
                "price": 0.00,
                "currency": "ALGO",
                "trial_days": 14,
                "is_active": True,
                "features": ["Basic API Access", "Email Support", "1 Project"]
            },
            {
                "name": "Pro",
                "description": "For growing businesses and builders",
                "price": 9.99,
                "currency": "ALGO",
                "trial_days": 7,
                "is_active": True,
                "features": ["Unlimited Projects", "Priority Email Support", "Analytics Dashboard"]
            },
            {
                "name": "Enterprise",
                "description": "Advanced features and custom support",
                "price": 49.99,
                "currency": "ALGO",
                "trial_days": 0,
                "is_active": True,
                "features": ["Custom SLAs", "Dedicated Support", "Webhook Logs", "Custom Integrations"]
            },
        ]

        for plan_data in plans:
            plan, created = SubscriptionPlan.objects.get_or_create(
                name=plan_data["name"],
                defaults={
                    "description": plan_data["description"],
                    "price": plan_data["price"],
                    "currency": plan_data["currency"],
                    "trial_days": plan_data["trial_days"],
                    "is_active": plan_data["is_active"],
                }
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"✅ Created plan: {plan.name}"))

                for feat in plan_data["features"]:
                    f = Feature.objects.create(name=feat, plan=plan)
                    self.stdout.write(f"   ➕ Feature added: {f.name}")
            else:
                self.stdout.write(self.style.WARNING(f"⚠️ Plan already exists: {plan.name}"))
