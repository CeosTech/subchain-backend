# ----------------------------------
# SERIALIZERS - accounts/serializers.py
# ----------------------------------
from rest_framework import serializers
from django.contrib.auth import get_user_model

from accounts.utils import send_verification_email
from .models import EmailVerification, UserProfile, UserSettings, UserActivity


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
	class Meta:
		model = User
		fields = ['id', 'email', 'username', 'wallet_address', 'is_verified']


class UserProfileSerializer(serializers.ModelSerializer):
	class Meta:
		model = UserProfile
		fields = '__all__'


class UserSettingsSerializer(serializers.ModelSerializer):
	class Meta:
		model = UserSettings
		fields = '__all__'


class UserActivitySerializer(serializers.ModelSerializer):
	class Meta:
		model = UserActivity
		fields = '__all__'
  
class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'password', 'username')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        token_obj = EmailVerification.objects.create(user=user)
        send_verification_email(user, token_obj.token)
        return user