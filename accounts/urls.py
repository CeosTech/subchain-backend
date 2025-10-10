from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from .views import (
LogoutView, UserListView, UserProfileView,
UserSettingsView, UserActivityListView, verify_email,
RegisterView, LoginView
)
from .views import me_view


urlpatterns = [
     path('register/', RegisterView.as_view(), name='register'),
     path('login/', LoginView.as_view(), name='login'),
     path('users/', UserListView.as_view(), name='user-list'),
     path('me/', me_view, name='me'),
     path('logout/', LogoutView.as_view(), name='logout'),
     path('verify-email/', verify_email),
     path('profile/', UserProfileView.as_view(), name='user-profile'),
     path('settings/', UserSettingsView.as_view(), name='user-settings'),
     path('activity/', UserActivityListView.as_view(), name='user-activity'),
     path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
     path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
     path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]