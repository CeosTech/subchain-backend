from django.core.management.base import BaseCommand
from notifications.models import NotificationTemplate

TEMPLATES = [
    {
        "name": "welcome_email",
        "subject": "Bienvenue sur SubChain 👋",
        "message": "Bonjour {{ user_name }},\n\nMerci de vous être inscrit sur SubChain. Commencez à explorer nos services dès maintenant !\n\nL'équipe SubChain 🚀",
        "notification_type": "email",
        "language": "fr",
    },
    {
        "name": "subscription_expiry_warning",
        "subject": "⏳ Votre abonnement expire bientôt",
        "message": "Bonjour {{ user_name }},\n\nVotre abonnement se termine le {{ expiry_date }}. Pensez à le renouveler pour éviter toute interruption.",
        "notification_type": "email",
        "language": "fr",
    },
    {
        "name": "payment_received",
        "subject": "✅ Paiement reçu",
        "message": "Bonjour {{ user_name }},\n\nNous avons bien reçu votre paiement de {{ amount }} {{ currency }}.\nMerci pour votre confiance.",
        "notification_type": "email",
        "language": "fr",
    },
    {
        "name": "trial_ending",
        "subject": "📆 Fin d’essai imminente",
        "message": "Bonjour {{ user_name }},\n\nVotre période d’essai gratuite se termine le {{ trial_end }}. Pensez à souscrire un abonnement pour continuer à utiliser SubChain.",
        "notification_type": "email",
        "language": "fr",
    },
]

class Command(BaseCommand):
    help = "Seed default notification templates"

    def handle(self, *args, **kwargs):
        created = 0
        for tpl in TEMPLATES:
            obj, was_created = NotificationTemplate.objects.get_or_create(
                name=tpl["name"],
                defaults={
                    "subject": tpl["subject"],
                    "message": tpl["message"],
                    "notification_type": tpl["notification_type"],
                    "language": tpl["language"],
                },
            )
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"✅ {created} notification templates créés."))
