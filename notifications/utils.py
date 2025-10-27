from django.template import Template, Context
from .models import NotificationTemplate

from django.core.mail import send_mail

import logging

logger = logging.getLogger(__name__)

def send_email_notification(notification):
    recipient = getattr(notification.user, "email", None)
    if not recipient:
        logger.warning("Notification %s has no associated user email.", notification.id)
        return False

    subject = notification.title or "Notification"
    try:
        send_mail(
            subject=subject,
            message=notification.message,
            from_email="no-reply@subchain.app",
            recipient_list=[recipient],
            fail_silently=False,
        )
        logger.info("Email sent to %s for notification %s", recipient, notification.id)
        return True
    except Exception as e:
        logger.error("Email error for notification %s: %s", notification.id, e)
        return False


def send_sms_notification(notification):
    # TODO: Intégration Twilio ou autre fournisseur SMS
    try:
        logger.info("Simulated SMS to %s: %s", notification.user, notification.message)
        return False  # still simulated, do not mark as sent
    except Exception as e:
        logger.error("SMS error for notification %s: %s", notification.id, e)
        return False


def render_template_text(text, context_dict):
    try:
        return Template(text).render(Context(context_dict))
    except Exception as e:
        return text  # fallback brut si erreur de contexte

def send_notification_from_template(template_name, user_email, context):
    try:
        tpl = NotificationTemplate.objects.get(name=template_name)

        subject = render_template_text(tpl.subject, context)
        message = render_template_text(tpl.message, context)

        if tpl.notification_type == "email":
            send_mail(
                subject=subject,
                message=message,
                from_email=None,  # fallback to DEFAULT_FROM_EMAIL
                recipient_list=[user_email],
                fail_silently=False,
            )
            return {"status": "sent", "method": "email"}
        else:
            return {"status": "error", "message": "Unsupported notification type"}
    except NotificationTemplate.DoesNotExist:
        return {"status": "error", "message": "Template not found"}
