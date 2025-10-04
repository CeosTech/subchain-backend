# subscriptions/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone

from payments.models import Transaction  # à créer ensuite
from .models import Feature, SubscriptionPlan, Subscriber, PlanChangeLog
from .serializers import (
    FeatureSerializer,
    SubscriptionPlanSerializer,
    SubscriberSerializer,
    PlanChangeLogSerializer,
)

class FeatureViewSet(viewsets.ModelViewSet):
    queryset = Feature.objects.all()
    serializer_class = FeatureSerializer
    permission_classes = [IsAdminUser]

class SubscriptionPlanViewSet(viewsets.ModelViewSet):
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [IsAdminUser]

class SubscriberViewSet(viewsets.ModelViewSet):
    queryset = Subscriber.objects.all()
    serializer_class = SubscriberSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Subscriber.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def subscribe(self, request):
        user = request.user
        plan_id = request.data.get('plan_id')
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id)
            subscriber, created = Subscriber.objects.get_or_create(user=user)
            previous_plan = subscriber.plan
            subscriber.plan = plan
            subscriber.status = 'trialing' if plan.trial_days > 0 else 'active'
            subscriber.start_date = timezone.now()
            if plan.trial_days:
                subscriber.trial_end_date = timezone.now() + timezone.timedelta(days=plan.trial_days)
            subscriber.renewal_date = timezone.now() + timezone.timedelta(days=30)
            subscriber.save()

            PlanChangeLog.objects.create(
                subscriber=subscriber,
                previous_plan=previous_plan,
                new_plan=plan
            )

            return Response({"message": "Subscription updated."}, status=status.HTTP_200_OK)
        except SubscriptionPlan.DoesNotExist:
            return Response({"error": "Plan not found."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def change_plan(self, request):
        user = request.user
        new_plan_id = request.data.get('plan_id')

        if not new_plan_id:
            return Response({'error': 'Plan ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            new_plan = SubscriptionPlan.objects.get(id=new_plan_id)
        except SubscriptionPlan.DoesNotExist:
            return Response({'error': 'Subscription plan not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            subscriber = Subscriber.objects.get(user=user)
        except Subscriber.DoesNotExist:
            return Response({'error': 'User does not have an active subscription.'}, status=status.HTTP_400_BAD_REQUEST)

        old_plan = subscriber.plan
        subscriber.plan = new_plan
        subscriber.start_date = timezone.now()
        subscriber.trial_end_date = None
        subscriber.renewal_date = timezone.now() + timezone.timedelta(days=30)
        subscriber.status = 'active'
        subscriber.save()

        PlanChangeLog.objects.create(
            subscriber=subscriber,
            previous_plan=old_plan,
            new_plan=new_plan,
        )

        return Response({'message': 'Subscription plan changed successfully.'}, status=status.HTTP_200_OK)
    

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def renew_subscription(request):
    user = request.user
    try:
        subscriber = Subscriber.objects.get(user=user)
        now = timezone.now()

        if subscriber.renewal_date and now >= subscriber.renewal_date:
            # Crée une transaction en ALGO
            tx = Transaction.objects.create(
                user=user,
                amount=subscriber.plan.price,
                currency=subscriber.plan.currency,
                status='pending',
                type='renewal'
            )

            # ➡️ (étape suivante : déclencher le swap ALGO ➜ USDC)

            # Prolonge l'abonnement
            subscriber.renewal_date = now + timezone.timedelta(days=30)
            subscriber.status = 'active'
            subscriber.save()

            return Response({"message": "Subscription renewed.", "transaction_id": tx.id}, status=200)

        return Response({"message": "Too early for renewal."}, status=400)

    except Subscriber.DoesNotExist:
        return Response({"error": "Subscriber not found."}, status=404)