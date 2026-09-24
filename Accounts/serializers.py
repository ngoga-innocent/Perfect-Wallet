# accounts/serializers.py

from rest_framework import serializers

from .models import Account


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = [
            "id",
            "name",
            "account_type",
            "currency",
            "balance",
            "is_active",
            "balance_updated_at",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "balance",
            "balance_updated_at",
            "created_at",
            "updated_at",
        ]

    def validate_currency(self, value):
        return value.upper()
