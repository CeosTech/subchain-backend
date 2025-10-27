# integrations/serializers.py

from rest_framework import serializers
from .models import Integration

class IntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Integration
        fields = "__all__"
        read_only_fields = [
            "id",
            "user",
            "created_at",
            "updated_at",
            "status",
            "last_success_at",
            "last_error_at",
            "failure_count",
            "last_error_message",
        ]
