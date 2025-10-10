from rest_framework import generics, permissions
from rest_framework.views import APIView

from accounts.utils import send_password_reset_email
from .models import EmailVerification, PasswordResetToken, UserProfile, UserSettings, UserActivity
from .serializers import (
UserSerializer, UserProfileSerializer,
UserSettingsSerializer, UserActivitySerializer
)
from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .serializers import RegisterSerializer, UserSerializer


User = get_user_model()


class UserListView(generics.ListAPIView):
	queryset = User.objects.all()
	serializer_class = UserSerializer
	permission_classes = [permissions.IsAdminUser]


class UserProfileView(generics.RetrieveUpdateAPIView):
	serializer_class = UserProfileSerializer
	permission_classes = [permissions.IsAuthenticated]

	def get_object(self):
		return self.request.user.profile


class UserSettingsView(generics.RetrieveUpdateAPIView):
	serializer_class = UserSettingsSerializer
	permission_classes = [permissions.IsAuthenticated]

	def get_object(self):
		return self.request.user.settings


class UserActivityListView(generics.ListAPIView):
	serializer_class = UserActivitySerializer
	permission_classes = [permissions.IsAuthenticated]

	def get_queryset(self):
		return UserActivity.objects.filter(user=self.request.user)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    user = request.user
    data = {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "wallet_address": user.wallet_address,
        "is_verified": user.is_verified,
    }
    return Response(data)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        

@api_view(['POST'])
def verify_email(request):
    token = request.data.get("token")
    try:
        token_obj = EmailVerification.objects.get(token=token)
        if token_obj.is_expired():
            return Response({"error": "Token expired"}, status=status.HTTP_400_BAD_REQUEST)
        user = token_obj.user
        user.is_verified = True
        user.save()
        token_obj.delete()
        return Response({"success": "Email verified"}, status=status.HTTP_200_OK)
    except EmailVerification.DoesNotExist:
        return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)
    

@api_view(['POST'])
def forgot_password(request):
    email = request.data.get('email')
    try:
        user = User.objects.get(email=email)
        token_obj = PasswordResetToken.objects.create(user=user)
        send_password_reset_email(user, token_obj.token)
        return Response({"message": "Reset email sent!"})
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

@api_view(['POST'])
def reset_password(request):
    token = request.data.get('token')
    new_password = request.data.get('new_password')
    try:
        reset = PasswordResetToken.objects.get(token=token, is_used=False)
        user = reset.user
        user.set_password(new_password)
        user.save()
        reset.is_used = True
        reset.save()
        return Response({"message": "Password reset successfully!"})
    except PasswordResetToken.DoesNotExist:
        return Response({"error": "Invalid or expired token"}, status=400)

class RegisterView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        if not email or not password:
            return Response({"detail": "Email and password required"}, status=status.HTTP_400_BAD_REQUEST)
        user = authenticate(request, username=email, password=password)
        if not user:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        })
