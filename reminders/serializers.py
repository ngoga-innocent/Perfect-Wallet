from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from .models import FinancialReminder


class FinancialReminderSerializer(
    serializers.ModelSerializer
):
    reminder_date = serializers.ReadOnlyField()

    class Meta:
        model = FinancialReminder

        fields = [
            "id",
            "name",
            "amount",
            "payment_date",
            "remind_days_before",
            "reminder_date",
            "recurrence",
            "status",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "reminder_date",
            "status",
            "created_at",
            "updated_at",
        ]

    def validate_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Reminder name is required."
            )

        return value

    def validate_amount(self, value):
        if value <= Decimal("0"):
            raise serializers.ValidationError(
                "Amount must be greater than zero."
            )

        return value

    def validate_remind_days_before(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "Reminder days cannot be negative."
            )

        return value

    def validate(self, attrs):
        payment_date = attrs.get(
            "payment_date",
            getattr(
                self.instance,
                "payment_date",
                None,
            ),
        )

        remind_days_before = attrs.get(
            "remind_days_before",
            getattr(
                self.instance,
                "remind_days_before",
                0,
            ),
        )

        if payment_date and not self.instance:
            reminder_date = (
                payment_date
                - timedelta(days=remind_days_before)
            )

            if reminder_date < timezone.localdate():
                raise serializers.ValidationError({
                    "remind_days_before": (
                        "The reminder period cannot start "
                        "before today."
                    )
                })

        return attrs
from rest_framework import serializers

from .models import UserDevice


class UserDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDevice
        fields = [
            "id",
            "expo_push_token",
            "platform",
            "device_name",
            "is_active",
            "created_at",
            "updated_at",
            "last_registered_at",
        ]
        read_only_fields = [
            "id",
            "is_active",
            "created_at",
            "updated_at",
            "last_registered_at",
        ]