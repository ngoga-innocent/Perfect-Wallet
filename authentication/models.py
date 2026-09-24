from django.contrib.auth.models import AbstractUser
from django.db import models
from .managers import UserManager
from django.conf import settings

class User(AbstractUser):

    
    username = None
    email = models.EmailField(
        unique=True
    )

    phone_number = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True
    )

    is_verified = models.BooleanField(
        default=False
    )


    USERNAME_FIELD = "email"

    REQUIRED_FIELDS = [ 'phone_number']
    objects = UserManager()
class UserSecurity(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="security"
    )


    pin_hash = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )


    totp_secret = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )


    authenticator_enabled = models.BooleanField(
        default=False
    )


    created_at = models.DateTimeField(
        auto_now_add=True
    )


    updated_at = models.DateTimeField(
        auto_now=True
    )


    def __str__(self):

        return self.user.email




class OTPVerification(models.Model):

    PURPOSE_CHOICES = (
        ("password_reset", "Password Reset"),
        ("pin_reset", "PIN Reset"),
        ("email_verification", "Email Verification"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="otp_verifications",
    )

    purpose = models.CharField(
        max_length=50,
        choices=PURPOSE_CHOICES,
    )

    otp_hash = models.CharField(
        max_length=255,
    )

    expires_at = models.DateTimeField()

    attempts = models.PositiveIntegerField(
        default=0,
    )

    max_attempts = models.PositiveIntegerField(
        default=5,
    )

    verified = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.purpose}"