# loans/models.py

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Loan(models.Model):
    class LoanType(models.TextChoices):
        LENT = "lent", "Money I Lent"
        BORROWED = "borrowed", "Money I Borrowed"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PAID = "paid", "Paid"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="loans",
    )

    person = models.CharField(
        max_length=255,
    )

    loan_type = models.CharField(
        max_length=10,
        choices=LoanType.choices,
    )

    principal_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01"))
        ],
    )

    remaining_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00"))
        ],
    )

    currency = models.CharField(
        max_length=3,
        default="RWF",
    )
    account = models.ForeignKey(
        "Accounts.Account",
        on_delete=models.PROTECT,
        related_name="loans",
        )
    payment_date = models.DateField(
        null=True,
        blank=True,
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "loan_type"]),
            models.Index(fields=["user", "status"]),
            models.Index(fields=["user", "payment_date"]),
        ]

    def __str__(self):
        return f"{self.person} - {self.principal_amount} {self.currency}"

    @property
    def paid_amount(self):
        return self.principal_amount - self.remaining_amount