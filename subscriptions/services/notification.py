from __future__ import annotations

from typing import Optional

from notifications.models import Notification
from notifications.utils import send_email_notification


class NotificationDispatcher:
    """Send human notifications when subscription or invoice events happen."""

    def subscription_created(self, subscription) -> Notification:
        title = "Subscription Created"
        message = f"Your subscription to {subscription.plan.name} has been created."
        return self._notify(subscription.user, title, message)

    def subscription_activated(self, subscription) -> Notification:
        title = "Subscription Activated"
        message = f"Your subscription to {subscription.plan.name} is now active."
        return self._notify(subscription.user, title, message)

    def subscription_canceled(self, subscription, *, immediate: bool) -> Notification:
        title = "Subscription Canceled"
        if immediate:
            message = "Your subscription has been canceled immediately."
        else:
            message = "Your subscription will end at the end of the current billing period."
        return self._notify(subscription.user, title, message)

    def subscription_resumed(self, subscription) -> Notification:
        title = "Subscription Resumed"
        message = f"Your subscription to {subscription.plan.name} has been resumed."
        return self._notify(subscription.user, title, message)

    def subscription_past_due(self, subscription, reason: Optional[str] = None) -> Notification:
        title = "Payment Required"
        message = "We were unable to process your recent payment. Please update your wallet to avoid interruption."
        if reason:
            message += f"\nReason: {reason}"
        return self._notify(subscription.user, title, message)

    def subscription_renewed(self, subscription) -> Notification:
        title = "Subscription Renewed"
        message = f"Your subscription to {subscription.plan.name} has been renewed."
        return self._notify(subscription.user, title, message)

    def subscription_ended(self, subscription) -> Notification:
        title = "Subscription Ended"
        message = "Your subscription has ended."
        return self._notify(subscription.user, title, message)

    def invoice_paid(self, invoice) -> Notification:
        title = "Payment Successful"
        message = f"Invoice {invoice.number} was paid successfully."
        return self._notify(invoice.user, title, message)

    def invoice_payment_failed(self, invoice, error: str) -> Notification:
        title = "Payment Failed"
        message = f"We could not process invoice {invoice.number}. Error: {error}"
        return self._notify(invoice.user, title, message)

    def _notify(self, user, title: str, message: str, channel: str = "email") -> Notification:
        notification = Notification.objects.create(
            user=user,
            title=title,
            message=message,
            channel=channel,
        )
        if channel == "email":
            send_email_notification(notification)
        return notification
