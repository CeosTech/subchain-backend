from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from payments.services import SwapExecutionError
from payments.models import TransactionType
from .models import (
    CheckoutSession,
    CheckoutSessionStatus,
    Coupon,
    EventLog,
    Invoice,
    InvoiceStatus,
    Plan,
    Subscription,
    SubscriptionStatus,
)
from .serializers import (
    CouponSerializer,
    CheckoutSessionSerializer,
    EventLogSerializer,
    InvoiceSerializer,
    PlanSerializer,
    SubscriptionSerializer,
    PaymentIntentSerializer,
)
from .services import InvoiceService, PaymentIntentService, SubscriptionLifecycleService


def execute_subscription_checkout(
    *,
    user,
    plan,
    wallet_address: str,
    quantity: int = 1,
    coupon=None,
    metadata=None,
    transaction_type: TransactionType = TransactionType.SUBSCRIPTION,
):
    lifecycle = SubscriptionLifecycleService()
    invoice_service = InvoiceService()
    payment_service = PaymentIntentService()

    lifecycle_result = lifecycle.create_subscription(
        user=user,
        plan=plan,
        wallet_address=wallet_address,
        coupon=coupon,
        quantity=quantity,
        metadata=metadata or {},
    )
    subscription = lifecycle_result.subscription

    invoice_status = (
        InvoiceStatus.DRAFT if subscription.status == SubscriptionStatus.TRIALING else InvoiceStatus.OPEN
    )
    invoice = invoice_service.create_invoice(
        subscription,
        status=invoice_status,
        coupon=coupon,
    )

    payment_intent = None
    payment_error = None
    if subscription.status != SubscriptionStatus.TRIALING:
        try:
            payment_intent = payment_service.process_invoice(
                invoice,
                transaction_type=transaction_type,
            )
        except SwapExecutionError as exc:
            lifecycle.mark_past_due(subscription, reason=str(exc))
            payment_error = str(exc)

    return subscription, invoice, payment_intent, payment_error


class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Plan.objects.filter(is_active=True)
    serializer_class = PlanSerializer
    permission_classes = [permissions.AllowAny]


class SubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Subscription.objects.all()
        return Subscription.objects.filter(user=user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        plan = validated["plan"]
        coupon = validated.get("coupon")
        quantity = validated.get("quantity") or 1
        wallet_address = validated["wallet_address"]
        metadata = validated.get("metadata", {})

        subscription, invoice, payment_intent, payment_error = execute_subscription_checkout(
            user=request.user,
            plan=plan,
            wallet_address=wallet_address,
            coupon=coupon,
            quantity=quantity,
            metadata=metadata,
            transaction_type=TransactionType.SUBSCRIPTION,
        )

        subscription_data = self.get_serializer(subscription).data
        invoice_data = InvoiceSerializer(invoice, context=self.get_serializer_context()).data
        payment_intent_data = PaymentIntentSerializer(payment_intent).data if payment_intent else None

        data = {
            "subscription": subscription_data,
            "invoice": invoice_data,
            "payment_intent": payment_intent_data,
        }
        if payment_error:
            data["payment_error"] = payment_error
        headers = self.get_success_headers(subscription_data)
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        subscription = self.get_object()
        at_period_end = request.data.get("at_period_end", True)
        lifecycle = SubscriptionLifecycleService()
        result = lifecycle.cancel_subscription(subscription, at_period_end=bool(at_period_end))
        return Response(self.get_serializer(result.subscription).data)

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        subscription = self.get_object()
        lifecycle = SubscriptionLifecycleService()
        result = lifecycle.resume_subscription(subscription)
        return Response(self.get_serializer(result.subscription).data)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        subscription = self.get_object()
        lifecycle = SubscriptionLifecycleService()
        result = lifecycle.activate_subscription(subscription)
        return Response(self.get_serializer(result.subscription).data)


class InvoiceViewSet(viewsets.ModelViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Invoice.objects.all()
        return Invoice.objects.filter(user=user)

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        invoice = self.get_object()
        payment_service = PaymentIntentService()
        try:
            payment_service.process_invoice(invoice, transaction_type=TransactionType.MANUAL)
        except SwapExecutionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        serializer = self.get_serializer(invoice)
        return Response(serializer.data)


class CouponViewSet(viewsets.ModelViewSet):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    permission_classes = [permissions.IsAdminUser]


class EventLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = EventLog.objects.all()
    serializer_class = EventLogSerializer
    permission_classes = [permissions.IsAdminUser]


class CheckoutSessionViewSet(viewsets.ModelViewSet):
    serializer_class = CheckoutSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return CheckoutSession.objects.all()
        return CheckoutSession.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        session = self.get_object()

        if session.status == CheckoutSessionStatus.COMPLETED:
            return Response({"detail": "Session already completed."}, status=status.HTTP_400_BAD_REQUEST)

        if session.is_expired:
            session.status = CheckoutSessionStatus.EXPIRED
            session.save(update_fields=["status", "updated_at"])
            return Response({"detail": "Session expired."}, status=status.HTTP_400_BAD_REQUEST)

        subscription, invoice, payment_intent, payment_error = execute_subscription_checkout(
            user=session.user,
            plan=session.plan,
            wallet_address=session.wallet_address,
            coupon=session.coupon,
            quantity=session.quantity,
            metadata=session.metadata,
            transaction_type=TransactionType.SUBSCRIPTION,
        )

        if payment_error:
            data = {
                "subscription": SubscriptionSerializer(subscription, context=self.get_serializer_context()).data,
                "invoice": InvoiceSerializer(invoice, context=self.get_serializer_context()).data,
                "payment_intent": PaymentIntentSerializer(payment_intent).data if payment_intent else None,
                "payment_error": payment_error,
            }
            return Response(data, status=status.HTTP_400_BAD_REQUEST)

        session.status = CheckoutSessionStatus.COMPLETED
        session.save(update_fields=["status", "updated_at"])

        data = {
            "subscription": SubscriptionSerializer(subscription, context=self.get_serializer_context()).data,
            "invoice": InvoiceSerializer(invoice, context=self.get_serializer_context()).data,
            "payment_intent": PaymentIntentSerializer(payment_intent).data if payment_intent else None,
        }
        return Response(data, status=status.HTTP_200_OK)
