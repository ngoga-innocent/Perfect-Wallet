from decimal import Decimal

from django.db.models import Q
from rest_framework import serializers

from Accounts.models import Account
from .models import Transaction

class InsufficientBalanceError(Exception):
    pass
class TransactionSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(
        source="account.name",
        read_only=True,
    )

    destination_account_name = serializers.CharField(
        source="destination_account.name",
        read_only=True,
    )

    class Meta:
        model = Transaction
        fields = [
            "id",
            "account",
            "account_name",
            "destination_account",
            "destination_account_name",
            "transaction_type",
            "amount",
            "category",
            "description",
            "transaction_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "account_name",
            "destination_account_name",
            "created_at",
            "updated_at",
        ]

    def validate_account(self, account):
        user = self.context["request"].user

        if account.owner_id != user.id:
            raise serializers.ValidationError(
                "You do not have access to this account."
            )

        return account

    def validate_destination_account(self, account):
        if account is None:
            return account

        user = self.context["request"].user

        if account.owner_id != user.id:
            raise serializers.ValidationError(
                "You do not have access to this account."
            )

        return account

    def validate(self, attrs):
        transaction_type = attrs.get(
            "transaction_type",
            getattr(self.instance, "transaction_type", None),
        )

        account = attrs.get(
            "account",
            getattr(self.instance, "account", None),
        )

        destination_account = attrs.get(
            "destination_account",
            getattr(self.instance, "destination_account", None),
        )

        amount = attrs.get(
            "amount",
            getattr(self.instance, "amount", None),
        )

        # -----------------------------------------
        # General amount validation
        # -----------------------------------------
        if amount is not None and amount <= Decimal("0"):
            raise serializers.ValidationError({
                "amount": "Amount must be greater than zero."
            })

        # -----------------------------------------
        # Income / Expense
        # -----------------------------------------
        if transaction_type in [
            Transaction.TransactionType.INCOME,
            Transaction.TransactionType.EXPENSE,
        ]:
            if destination_account is not None:
                raise serializers.ValidationError({
                    "destination_account": (
                        "Destination account is only allowed for transfers."
                    )
                })

        # -----------------------------------------
        # Transfer
        # -----------------------------------------
        if transaction_type == Transaction.TransactionType.TRANSFER:
            if destination_account is None:
                raise serializers.ValidationError({
                    "destination_account": (
                        "Destination account is required for transfers."
                    )
                })

            if account and destination_account:
                if account.pk == destination_account.pk:
                    raise serializers.ValidationError({
                        "destination_account": (
                            "Source and destination accounts "
                            "must be different."
                        )
                    })

        return attrs

    def create(self, validated_data):
        user = self.context["request"].user

        return Transaction.objects.create(
            user=user,
            **validated_data,
        )