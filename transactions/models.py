# transactions/models.py

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from decimal import Decimal

class Transaction(models.Model):
    class TransactionType(models.TextChoices):
        INCOME = "income", "Income"
        EXPENSE = "expense", "Expense"
        TRANSFER = "transfer", "Transfer"
        LOAN = "loan", "Loan"
    class LoanTransactionType(models.TextChoices):
        INITIAL = "initial", "Initial Loan"
        REPAYMENT = "repayment", "Loan Repayment"
    id = models.BigAutoField(primary_key=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transactions",
    )

    account = models.ForeignKey(
        "Accounts.Account",
        on_delete=models.PROTECT,
        related_name="transactions",
    )

    # Only required when type == TRANSFER
    destination_account = models.ForeignKey(
        "Accounts.Account",
        on_delete=models.PROTECT,
        related_name="incoming_transfers",
        null=True,
        blank=True,
    )
    loan = models.ForeignKey(
        "loans.Loan",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="transactions",
        )
    loan_transaction_type = models.CharField(
            max_length=20,
            choices=LoanTransactionType.choices,
            null=True,
            blank=True,
        )
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
    )

    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01"))
        ],
    )

    description = models.CharField(
        max_length=255,
        blank=True,
    )

    # Useful later for expense/income categorization
    category = models.CharField(
        max_length=100,
        blank=True,
    )

    transaction_date = models.DateTimeField(auto_now_add=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-transaction_date", "-created_at"]
        indexes = [
            models.Index(fields=["user", "-transaction_date"]),
            models.Index(fields=["account", "-transaction_date"]),
            models.Index(fields=["transaction_type", "-transaction_date"]),
        ]

    def __str__(self):
        return (
            f"{self.transaction_type} - "
            f"{self.amount} - "
            f"{self.account}"
        )