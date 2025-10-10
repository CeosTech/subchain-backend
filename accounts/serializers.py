# ----------------------------------
# SERIALIZERS - accounts/serializers.py
# ----------------------------------
from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework.validators import UniqueValidator

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
    email = serializers.EmailField(validators=[UniqueValidator(queryset=User.objects.all())])
    wallet_address = serializers.CharField(validators=[UniqueValidator(queryset=User.objects.all())])
    class Meta:
        model = User
        fields = ('email', 'password', 'username', 'wallet_address')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        email = validated_data.get('email')
        password = validated_data.get('password')
        username = validated_data.get('username') or (email.split('@')[0] if email else None)
        wallet_address = validated_data.get('wallet_address')

        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                wallet_address=wallet_address,
            )
        except Exception as e:
            raise serializers.ValidationError({"detail": "Unable to create user"})
        token_obj = EmailVerification.objects.create(user=user)
        send_verification_email(user, token_obj.token)
        return user