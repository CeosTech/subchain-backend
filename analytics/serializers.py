# analytics/serializers.py
from rest_framework import serializers
from .models import AnalyticsLog

class AnalyticsLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsLog
        fields = '__all__'
        read_only_fields = ('user', 'timestamp')



