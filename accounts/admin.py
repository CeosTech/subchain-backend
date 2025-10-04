from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import UserProfile, UserSettings, UserActivity, EmailVerification


User = get_user_model()


admin.site.register(User)
admin.site.register(UserProfile)
admin.site.register(UserSettings)
admin.site.register(UserActivity)
admin.site.register(EmailVerification)