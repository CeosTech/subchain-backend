import uuid
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


# -----------------------------
# MODELS - accounts/models.py
# -----------------------------


class User(AbstractUser):
	email = models.EmailField(unique=True)
	wallet_address = models.CharField(max_length=255, unique=True)
	is_verified = models.BooleanField(default=False)
	USERNAME_FIELD = 'email'
	REQUIRED_FIELDS = ['username']


class UserProfile(models.Model):
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
	company_name = models.CharField(max_length=255, blank=True, null=True)
	is_individual = models.BooleanField(default=True)
	phone_number = models.CharField(max_length=20, blank=True, null=True)
	address = models.TextField(blank=True, null=True)
	country = models.CharField(max_length=100, blank=True, null=True)


class UserSettings(models.Model):
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='settings')
	language = models.CharField(max_length=10, default='en')
	timezone = models.CharField(max_length=50, default='UTC')
	receive_emails = models.BooleanField(default=True)


class UserActivity(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
	action = models.CharField(max_length=255)
	ip_address = models.GenericIPAddressField(null=True, blank=True)
	timestamp = models.DateTimeField(default=timezone.now)


class EmailVerification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"EmailVerification for {self.user.email}"
    
    def is_expired(self, validity_hours=24):
        expiry_time = self.created_at + timezone.timedelta(hours=validity_hours)
        return timezone.now() > expiry_time
    
class PasswordResetToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"Reset token for {self.user.email}"
