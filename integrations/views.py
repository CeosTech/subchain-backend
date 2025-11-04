# integrations/views.py

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import (
    CreditSubscription,
    CreditUsage,
    EndpointPricingRule,
    Integration,
    PaymentLink,
    PaymentLinkType,
    PaymentReceipt,
    X402CreditPlan,
    CreditUsageType,
)
from .serializers import (
    CreditPlanSerializer,
    CreditSubscriptionSerializer,
    CreditUsageSerializer,
    EndpointPricingRuleSerializer,
    IntegrationSerializer,
    PaymentLinkSerializer,
    PaymentReceiptSerializer,
    PaymentWidgetSerializer,
)
from .services import (
    deactivate_pricing_rule,
    sync_pricing_rule_for_credit_plan,
    sync_pricing_rule_for_link,
)


class IntegrationViewSet(viewsets.ModelViewSet):
    serializer_class = IntegrationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Integration.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class EndpointPricingRuleViewSet(viewsets.ModelViewSet):
    serializer_class = EndpointPricingRuleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return EndpointPricingRule.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PaymentReceiptViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentReceiptSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            queryset = PaymentReceipt.objects.all().order_by("-created_at")
        else:
            queryset = PaymentReceipt.objects.filter(user=self.request.user).order_by("-created_at")
        status_value = self.request.query_params.get("status")
        if status_value:
            queryset = queryset.filter(status=status_value)
        path_value = self.request.query_params.get("path")
        if path_value:
            queryset = queryset.filter(request_path__icontains=path_value)
        method_value = self.request.query_params.get("method")
        if method_value:
            queryset = queryset.filter(request_method__iexact=method_value.upper())
        return queryset


class _BasePaymentLinkViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    kind = PaymentLinkType.LINK
    serializer_class = PaymentLinkSerializer

    def get_queryset(self):
        return PaymentLink.objects.filter(user=self.request.user, kind=self.kind).order_by("-created_at")

    def perform_create(self, serializer):
        link = serializer.save(user=self.request.user, kind=self.kind)
        sync_pricing_rule_for_link(link)

    def perform_update(self, serializer):
        link = serializer.save()
        sync_pricing_rule_for_link(link)

    def perform_destroy(self, instance):
        deactivate_pricing_rule(instance.user_id, instance.get_paywall_path())
        instance.delete()


class PaymentLinkViewSet(_BasePaymentLinkViewSet):
    serializer_class = PaymentLinkSerializer
    kind = PaymentLinkType.LINK


class PaymentWidgetViewSet(_BasePaymentLinkViewSet):
    serializer_class = PaymentWidgetSerializer
    kind = PaymentLinkType.WIDGET


class CreditPlanViewSet(viewsets.ModelViewSet):
    serializer_class = CreditPlanSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return X402CreditPlan.objects.filter(user=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        plan = serializer.save(user=self.request.user)
        sync_pricing_rule_for_credit_plan(plan)

    def perform_update(self, serializer):
        plan = serializer.save()
        sync_pricing_rule_for_credit_plan(plan)

    def perform_destroy(self, instance):
        deactivate_pricing_rule(instance.user_id, instance.build_pattern())
        instance.delete()


class CreditSubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CreditSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = CreditSubscription.objects.filter(plan__user=self.request.user).order_by("-updated_at")
        plan_id = self.request.query_params.get("plan")
        if plan_id:
            queryset = queryset.filter(plan_id=plan_id)
        consumer = self.request.query_params.get("consumer")
        if consumer:
            queryset = queryset.filter(consumer_ref=consumer)
        return queryset

    @action(detail=True, methods=["post"], url_path="consume")
    def consume(self, request, pk=None):
        subscription = self.get_object()
        credits = request.data.get("credits", 1)
        try:
            credits = int(credits)
        except (TypeError, ValueError):
            return Response({"detail": "credits must be an integer."}, status=status.HTTP_400_BAD_REQUEST)
        if credits <= 0:
            return Response({"detail": "credits must be positive."}, status=status.HTTP_400_BAD_REQUEST)
        if subscription.credits_remaining < credits:
            return Response({"detail": "Insufficient credits."}, status=status.HTTP_400_BAD_REQUEST)

        subscription.credits_remaining -= credits
        subscription.save(update_fields=["credits_remaining", "updated_at"])
        usage = CreditUsage.objects.create(
            subscription=subscription,
            usage_type=CreditUsageType.CONSUMPTION,
            credits_delta=-credits,
            description=request.data.get("description", "Manual consumption"),
            metadata=request.data.get("metadata") or {},
        )
        serializer = CreditUsageSerializer(usage)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CreditUsageViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CreditUsageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = CreditUsage.objects.filter(subscription__plan__user=self.request.user).order_by("-created_at")
        plan_id = self.request.query_params.get("plan")
        if plan_id:
            queryset = queryset.filter(subscription__plan_id=plan_id)
        subscription_id = self.request.query_params.get("subscription")
        if subscription_id:
            queryset = queryset.filter(subscription_id=subscription_id)
        consumer = self.request.query_params.get("consumer")
        if consumer:
            queryset = queryset.filter(subscription__consumer_ref=consumer)
        usage_type = self.request.query_params.get("type")
        if usage_type:
            queryset = queryset.filter(usage_type=usage_type)
        return queryset
