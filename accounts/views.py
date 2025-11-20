# accounts/views.py

import logging

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.utils import send_password_reset_email, send_verification_email
from .models import (
    EmailVerification,
    PasswordResetToken,
    UserProfile,
    UserSettings,
    UserActivity,
)
from .serializers import (
    UserSerializer,
    UserProfileSerializer,
    UserSettingsSerializer,
    UserActivitySerializer,
    RegisterSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()


# -------------------------------------------------------
# USERS LIST / PROFILE / SETTINGS / ACTIVITY
# -------------------------------------------------------


class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # On garantit qu'un profil existe pour éviter un DoesNotExist -> 500
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile


class UserSettingsView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSettingsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # On garantit que les settings existent
        settings_obj, _ = UserSettings.objects.get_or_create(user=self.request.user)
        return settings_obj


class UserActivityListView(generics.ListAPIView):
    serializer_class = UserActivitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserActivity.objects.filter(user=self.request.user)


# -------------------------------------------------------
# CURRENT USER / LOGOUT
# -------------------------------------------------------


@api_view(["GET"])
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
        except Exception:
            logger.exception("Erreur lors du logout / blacklist du refresh token")
            return Response(status=status.HTTP_400_BAD_REQUEST)


# -------------------------------------------------------
# EMAIL VERIFICATION
# -------------------------------------------------------


@api_view(["POST"])
@permission_classes([AllowAny])
def verify_email(request):
    token = request.data.get("token")
    if not token:
        return Response(
            {"error": "Token is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        token_obj = EmailVerification.objects.get(token=token)
    except EmailVerification.DoesNotExist:
        return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)

    if token_obj.is_used:
        return Response(
            {"error": "Token already used"}, status=status.HTTP_400_BAD_REQUEST
        )

    if token_obj.is_expired():
        return Response({"error": "Token expired"}, status=status.HTTP_400_BAD_REQUEST)

    user = token_obj.user
    user.is_verified = True
    user.save(update_fields=["is_verified"])
    token_obj.is_used = True
    token_obj.save(update_fields=["is_used"])

    return Response({"success": "Email verified"}, status=status.HTTP_200_OK)


# -------------------------------------------------------
# PASSWORD RESET
# -------------------------------------------------------


@api_view(["POST"])
@permission_classes([AllowAny])
def forgot_password(request):
    email = request.data.get("email")
    if not email:
        return Response(
            {"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    user = User.objects.filter(email=email).first()
    generic_response = Response(
        {"message": "If an account exists, reset instructions have been sent."},
        status=status.HTTP_200_OK,
    )
    if not user:
        logger.info("Password reset requested for unknown email: %s", email)
        return generic_response

    try:
        token_obj = PasswordResetToken.objects.create(user=user)
        send_password_reset_email(user, token_obj.token)
    except Exception:
        logger.exception("Erreur lors de la génération ou de l'envoi du reset password")
        # On évite de donner trop de détails côté client
        return Response(
            {"error": "Unable to send reset email"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return generic_response


@api_view(["POST"])
@permission_classes([AllowAny])
def reset_password(request):
    token = request.data.get("token")
    new_password = request.data.get("new_password")

    if not token or not new_password:
        return Response(
            {"error": "Token and new_password are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        reset = PasswordResetToken.objects.get(token=token, is_used=False)
    except PasswordResetToken.DoesNotExist:
        return Response(
            {"error": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST
        )
    if reset.is_expired():
        reset.is_used = True
        reset.save(update_fields=["is_used"])
        return Response(
            {"error": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST
        )

    user = reset.user
    user.set_password(new_password)
    user.save()
    reset.is_used = True
    reset.save()

    return Response({"message": "Password reset successfully!"}, status=status.HTTP_200_OK)


# -------------------------------------------------------
# REGISTER / LOGIN
# -------------------------------------------------------


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 1) Création du user
        try:
            user = serializer.save()
        except Exception:
            logger.exception("Erreur lors de la création de l'utilisateur")
            return Response(
                {"detail": "Unable to create user"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if getattr(settings, "SKIP_EMAIL_VERIFICATION", False):
            user.is_verified = True
            user.save(update_fields=["is_verified"])
            return Response(
                {
                    "detail": "User created. Email verification skipped for demo mode.",
                    "user": UserSerializer(user).data,
                },
                status=status.HTTP_201_CREATED,
            )

        # 2) Création du token de vérification
        try:
            token_obj = EmailVerification.objects.create(user=user)
        except Exception:
            logger.exception("Erreur lors de la création du token de vérification")
            return Response(
                {
                    "detail": "User created but email verification token failed.",
                    "user": UserSerializer(user).data,
                },
                status=status.HTTP_201_CREATED,
            )

        # 3) Envoi de l'email (non bloquant pour l'API)
        try:
            send_verification_email(user, token_obj.token)
        except Exception:
            logger.exception("Erreur lors de l'envoi de l'email de vérification")
            return Response(
                {
                    "detail": "User created but verification email could not be sent.",
                    "user": UserSerializer(user).data,
                },
                status=status.HTTP_201_CREATED,
            )

        # 4) Tout est ok → informer l'utilisateur qu'il doit vérifier son email
        return Response(
            {
                "detail": "User created. Please verify your email before logging in.",
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response(
                {"detail": "Email and password required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(request, username=email, password=password)
        if not user:
            return Response(
                {"detail": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if not getattr(settings, "SKIP_EMAIL_VERIFICATION", False) and not user.is_verified:
            return Response(
                {
                    "detail": "Email not verified. Please verify your email to continue."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )
