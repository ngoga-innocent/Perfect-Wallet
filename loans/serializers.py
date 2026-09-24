# loans/serializers.py

from decimal import Decimal

from rest_framework import serializers

from Accounts.models import Account

from .models import Loan

from decimal import Decimal



from .models import Loan
class LoanSerializer(serializers.ModelSerializer):
    account = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects.all(),
    )

    paid_amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = Loan

        fields = [
            "id",
            "person",
            "loan_type",
            "principal_amount",
            "remaining_amount",
            "paid_amount",
            "currency",
            "account",
            "payment_date",
            "description",
            "status",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "remaining_amount",
            "paid_amount",
            "status",
            "created_at",
            "updated_at",
        ]

    def validate_account(self, account):
        """
        Make sure the selected account belongs to
        the authenticated user and is active.
        """

        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError(
                "Authentication is required."
            )

        if account.owner_id != request.user.id:
            raise serializers.ValidationError(
                "You cannot use an account that does not belong to you."
            )

        if not account.is_active:
            raise serializers.ValidationError(
                "The selected account is not active."
            )

        return account

    def validate_principal_amount(self, value):
        if value <= Decimal("0"):
            raise serializers.ValidationError(
                "Amount must be greater than zero."
            )

        return value

    def validate_currency(self, value):
        return value.upper()

    def validate(self, attrs):
        """
        Validate the relationship between the loan
        and the selected account.
        """

        account = attrs.get("account")

        # On PATCH, account may not be included.
        if account is None:
            return attrs

        currency = attrs.get(
            "currency",
            account.currency,
        )

        if currency.upper() != account.currency.upper():
            raise serializers.ValidationError({
                "currency": (
                    f"Loan currency ({currency.upper()}) must match "
                    f"account currency ({account.currency.upper()})."
                )
            })

        return attrs



class LoanPaymentSerializer(serializers.Serializer):

    amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
    )

    account = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects.all(),
    )

    payment_date = serializers.DateField(
        required=False,
        allow_null=True,
    )

    description = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    def validate_amount(self, value):
        if value <= Decimal("0"):
            raise serializers.ValidationError(
                "Payment amount must be greater than zero."
            )

        return value

    def validate_account(self, account):
        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError(
                "Authentication is required."
            )

        if account.owner_id != request.user.id:
            raise serializers.ValidationError(
                "You cannot use an account that does not belong to you."
            )

        if not account.is_active:
            raise serializers.ValidationError(
                "The selected account is not active."
            )

        return account