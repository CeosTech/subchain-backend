# subscriptions/serializers.py
from rest_framework import serializers
from .models import Feature, SubscriptionPlan, Subscriber, PlanChangeLog

class FeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = '__all__'

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    features = FeatureSerializer(many=True, read_only=True)

    class Meta:
        model = SubscriptionPlan
        fields = '__all__'

class SubscriberSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)

    class Meta:
        model = Subscriber
        fields = '__all__'

class PlanChangeLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanChangeLog
        fields = '__all__'


