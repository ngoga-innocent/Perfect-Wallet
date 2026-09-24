# accounts/models.py

from decimal import Decimal

from django.conf import settings
from django.db import models


class Account(models.Model):
    class AccountType(models.TextChoices):
        CASH = "cash", "Cash"
        BANK = "bank", "Bank"
        MOBILE_MONEY = "mobile_money", "Mobile Money"
        SAVINGS = "savings", "Savings"
        OTHER = "other", "Other"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="accounts",
    )

    name = models.CharField(max_length=100)

    account_type = models.CharField(
        max_length=30,
        choices=AccountType.choices,
        default=AccountType.BANK,
    )

    currency = models.CharField(
        max_length=3,
        default="RWF",
    )

    balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    is_active = models.BooleanField(default=True)

    balance_updated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "name"],
                name="unique_account_name_per_owner",
            )
        ]

    def __str__(self):
        return f"{self.name} - {self.currency}"
class PushDevice(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="push_devices",
    )

    expo_push_token = models.CharField(
        max_length=255,
        unique=True,
    )

    device_type = models.CharField(
        max_length=20,
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]