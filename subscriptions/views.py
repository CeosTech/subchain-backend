import base64
import io

from django.conf import settings
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView

from payments.services import SwapExecutionError
from payments.models import TransactionType
import qrcode
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
    PublicPlanSerializer,
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
    **subscription_fields,
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
        **subscription_fields,
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


class PlanPublicRetrieveView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, code: str):
        plan = get_object_or_404(Plan, code=code, is_active=True)
        plan_data = PublicPlanSerializer(plan, context={"request": request}).data
        share_url = f"{settings.CHECKOUT_BASE_URL.rstrip('/')}/pay?plan={plan.code}"
        return Response({"plan": plan_data, "share_url": share_url})


class PlanViewSet(viewsets.ModelViewSet):
    queryset = Plan.objects.all()
    serializer_class = PlanSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        queryset = Plan.objects.all()
        user = getattr(self.request, "user", None)

        if self.action in ["list", "retrieve"]:
            if user and user.is_authenticated:
                if user.is_staff:
                    return queryset
                return queryset.filter(Q(created_by=user) | Q(is_active=True))
            return queryset.filter(is_active=True)

        if user and user.is_authenticated and not user.is_staff:
            return queryset.filter(created_by=user)
        return queryset

    def perform_create(self, serializer):
        payout_address = serializer.validated_data.get("payout_wallet_address")
        if not payout_address:
            payout_address = getattr(self.request.user, "wallet_address", "")
        serializer.save(created_by=self.request.user, payout_wallet_address=payout_address or "")

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def share(self, request, pk=None):
        plan = self.get_object()
        if not request.user.is_staff and plan.created_by_id != request.user.id:
            raise PermissionDenied("You can only share plans you created.")

        share_url = f"{settings.CHECKOUT_BASE_URL.rstrip('/')}/pay?plan={plan.code}"
        qr = qrcode.QRCode(box_size=4, border=2)
        qr.add_data(share_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode("ascii")

        return Response(
            {
                "share_url": share_url,
                "qr_code": f"data:image/png;base64,{qr_base64}",
            }
        )


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
        subscription_kwargs = {
            "customer_type": validated.get("customer_type"),
            "company_name": validated.get("company_name", ""),
            "vat_number": validated.get("vat_number", ""),
            "billing_email": validated.get("billing_email"),
            "billing_phone": validated.get("billing_phone", ""),
            "billing_address": validated.get("billing_address", ""),
            "billing_same_as_shipping": validated.get("billing_same_as_shipping", True),
            "shipping_address": validated.get("shipping_address", ""),
        }

        subscription, invoice, payment_intent, payment_error = execute_subscription_checkout(
            user=request.user,
            plan=plan,
            wallet_address=wallet_address,
            coupon=coupon,
            quantity=quantity,
            metadata=metadata,
            transaction_type=TransactionType.SUBSCRIPTION,
            **subscription_kwargs,
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
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Coupon.objects.all()
        return Coupon.objects.filter(Q(created_by=user) | Q(created_by__isnull=True))

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.instance
        user = self.request.user
        if not user.is_staff and instance.created_by != user:
            raise PermissionDenied("You can only update your own coupons.")
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        if not user.is_staff and instance.created_by != user:
            raise PermissionDenied("You can only delete your own coupons.")
        instance.delete()


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
            customer_type=session.customer_type,
            company_name=session.company_name,
            vat_number=session.vat_number,
            billing_email=session.billing_email,
            billing_phone=session.billing_phone,
            billing_address=session.billing_address,
            billing_same_as_shipping=session.billing_same_as_shipping,
            shipping_address=session.shipping_address,
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
