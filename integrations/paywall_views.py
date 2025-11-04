from __future__ import annotations

from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View

from .models import (
    CreditSubscription,
    PaymentLink,
    PaymentLinkType,
    PaymentReceipt,
    X402CreditPlan,
)


class PaymentLinkPaywallView(View):
    http_method_names = ["get"]

    def get(self, request, tenant_id: int, slug: str):
        link = get_object_or_404(PaymentLink, user_id=tenant_id, slug=slug, is_active=True)

        payment_context = getattr(request, "x402_payment", None)
        if not payment_context:
            # Middleware should have already issued 402, but guard just in case
            raise Http404("Payment context missing")

        receipt_id = payment_context.get("receipt_id")
        receipt = PaymentReceipt.objects.filter(id=receipt_id).first()

        payload = {
            "name": link.name,
            "description": link.description,
            "amount": str(link.amount),
            "currency": link.currency,
            "network": link.network,
            "success_url": link.success_url,
            "callback_url": link.callback_url,
            "pay_to_address": link.pay_to_address,
            "platform_fee_percent": str(link.platform_fee_percent),
            "metadata": link.metadata,
            "receipt_id": receipt_id,
            "payer_address": payment_context.get("payer"),
        }
        if receipt:
            payload["receipt_status"] = receipt.status
            payload["event_count"] = link.events.filter(receipt=receipt).count()

        if link.kind == PaymentLinkType.WIDGET:
            payload["widget"] = link.metadata

        return JsonResponse(payload)


class CreditPlanPaywallView(View):
    http_method_names = ["get"]

    def get_consumer_ref(self, request):
        return (
            request.GET.get("consumer")
            or request.GET.get("customer")
            or request.headers.get("X-Consumer-ID")
            or request.headers.get("X-Customer-ID")
        )

    def get(self, request, tenant_id: int, slug: str):
        plan = get_object_or_404(X402CreditPlan, user_id=tenant_id, slug=slug, is_active=True)
        payment_context = getattr(request, "x402_payment", None)
        if not payment_context:
            raise Http404("Payment context missing")

        consumer = self.get_consumer_ref(request) or payment_context.get("consumer") or payment_context.get("payer")
        if not consumer:
            consumer = payment_context.get("payer") or "anonymous"

        subscription = CreditSubscription.objects.filter(plan=plan, consumer_ref=consumer).order_by("-updated_at").first()

        payload = {
            "plan": {
                "name": plan.name,
                "description": plan.description,
                "amount": str(plan.amount),
                "currency": plan.currency,
                "network": plan.network,
                "credits_per_payment": plan.credits_per_payment,
                "auto_renew": plan.auto_renew,
                "pay_to_address": plan.pay_to_address,
                "platform_fee_percent": str(plan.platform_fee_percent),
            },
            "consumer": str(consumer),
            "receipt_id": payment_context.get("receipt_id"),
        }

        if subscription:
            payload["subscription"] = {
                "credits_remaining": subscription.credits_remaining,
                "total_credits": subscription.total_credits,
                "last_purchase_at": subscription.last_purchase_at,
            }

        return JsonResponse(payload)
