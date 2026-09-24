from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class FinancialReminder(models.Model):

    class Recurrence(models.TextChoices):
        NONE = "none", "No Repeat"
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="financial_reminders",
    )

    name = models.CharField(
        max_length=255,
    )

    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01")),
        ],
    )

    payment_date = models.DateField()

    # Number of days before payment_date to start notifications.
    remind_days_before = models.PositiveIntegerField(
        default=0,
    )

    recurrence = models.CharField(
        max_length=10,
        choices=Recurrence.choices,
        default=Recurrence.NONE,
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["payment_date", "-created_at"]

        indexes = [
            models.Index(
                fields=["user", "payment_date"]
            ),
            models.Index(
                fields=["user", "status"]
            ),
        ]

    def __str__(self):
        return f"{self.name} - {self.amount}"

    @property
    def reminder_date(self):
        """
        The date on which reminders should start.
        """
        from datetime import timedelta

        return self.payment_date - timedelta(
            days=self.remind_days_before
        )
from django.conf import settings
from django.db import models


class ReminderNotification(models.Model):

    class Channel(models.TextChoices):
        EMAIL = "email", "Email"
        PUSH = "push", "Push"

    reminder = models.ForeignKey(
        "FinancialReminder",
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reminder_notifications",
    )

    notification_date = models.DateField()

    channel = models.CharField(
        max_length=10,
        choices=Channel.choices,
    )

    sent_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "reminder",
                    "notification_date",
                    "channel",
                ],
                name="unique_reminder_notification",
            )
        ]

    def __str__(self):
        return (
            f"{self.reminder.name} - "
            f"{self.notification_date} - "
            f"{self.channel}"
        )
from django.conf import settings
from django.db import models
from django.utils import timezone


class UserDevice(models.Model):
    PLATFORM_CHOICES = (
        ("ios", "iOS"),
        ("android", "Android"),
        ("unknown", "Unknown"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="devices",
    )

    expo_push_token = models.CharField(
        max_length=255,
        unique=True,
    )

    device_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    platform = models.CharField(
        max_length=20,
        choices=PLATFORM_CHOICES,
        default="unknown",
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    last_registered_at = models.DateTimeField(
        default=timezone.now,
    )

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user} - {self.expo_push_token}"