from django.core.mail import send_mail
from django.conf import settings

def send_verification_email(user, token):
    subject = "Verify your email - SubChain"
    verification_link = f"{settings.FRONTEND_BASE_URL}/verify-email/{token}"
    message = f"Hi {user.username},\n\nClick the link below to verify your email:\n{verification_link}\n\nThank you!"
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])

def send_password_reset_email(user, token):
    subject = "Reset your password - SubChain"
    reset_link = f"{settings.FRONTEND_BASE_URL}/reset-password/{token}"
    message = f"Hi {user.username},\n\nClick the link below to reset your password:\n{reset_link}\n\nIf you didn’t request this, ignore this email."
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
