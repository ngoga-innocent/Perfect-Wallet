import logging
from decimal import Decimal

from django.db import IntegrityError, transaction as db_transaction
from django.utils import timezone

from rest_framework import status, viewsets,filters
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from Accounts.models import Account
from common.responses import ApiResponse

from .models import Transaction
from .serializers import TransactionSerializer
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count
from rest_framework.decorators import action
from django.db import models
from .filters import TransactionFilter
from django.shortcuts import get_object_or_404

logger = logging.getLogger(__name__)


class TransactionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing transactions.

    All transaction operations are performed atomically so that the
    transaction record and account balances remain consistent.

    Users can only access their own transactions and accounts.
    """

    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_class = TransactionFilter

    search_fields = [
        "description",
        "category",
    ]

    ordering_fields = [
        "transaction_date",
        "created_at",
        "amount",
    ]

    ordering = [
        "-transaction_date",
        "-created_at",
    ]

    def get_queryset(self):
        return (
            Transaction.objects
            .filter(user=self.request.user)
            .select_related(
                "account",
                "destination_account",
            )
        )

    # ============================================================
    # Account helpers
    # ============================================================

    def _lock_accounts(self, accounts):
        """
        Lock all involved accounts for the current database transaction.

        select_for_update() prevents concurrent transactions from modifying
        the same account balance at the same time.
        """
        ids = {
            account.pk
            for account in accounts
            if account is not None
        }

        return (
            Account.objects
            .select_for_update()
            .filter(pk__in=ids)
        )

    def _validate_sufficient_balance(
        self,
        account,
        amount,
    ):
        """
        Ensure the account has enough money for an outgoing transaction.
        """

        balance = account.balance or Decimal("0")

        if balance < amount:
            raise ValidationError({
                "code": "INSUFFICIENT_BALANCE",
                "detail": (
                    f"Insufficient balance in account "
                    f"'{account.name}'. "
                    f"Available balance: {balance}, "
                    f"requested: {amount}."
                ),
            })

    # ============================================================
    # Transaction effects
    # ============================================================

    def _apply_effect(self, tx):
        """
        Apply the financial effect of a transaction.

        This method assumes all affected accounts have already been locked.
        """

        now = timezone.now()

        if tx.transaction_type == Transaction.TransactionType.INCOME:

            tx.account.balance = (
                tx.account.balance or Decimal("0")
            ) + tx.amount

            tx.account.balance_updated_at = now

            tx.account.save(
                update_fields=[
                    "balance",
                    "balance_updated_at",
                ]
            )

        elif tx.transaction_type == Transaction.TransactionType.EXPENSE:

            self._validate_sufficient_balance(
                tx.account,
                tx.amount,
            )

            tx.account.balance = (
                tx.account.balance or Decimal("0")
            ) - tx.amount

            tx.account.balance_updated_at = now

            tx.account.save(
                update_fields=[
                    "balance",
                    "balance_updated_at",
                ]
            )

        elif tx.transaction_type == Transaction.TransactionType.TRANSFER:

            self._validate_sufficient_balance(
                tx.account,
                tx.amount,
            )

            if tx.destination_account is None:
                raise ValidationError({
                    "code": "INVALID_TRANSFER",
                    "detail": (
                        "A destination account is required "
                        "for transfers."
                    ),
                })

            # Source
            tx.account.balance = (
                tx.account.balance or Decimal("0")
            ) - tx.amount

            tx.account.balance_updated_at = now

            tx.account.save(
                update_fields=[
                    "balance",
                    "balance_updated_at",
                ]
            )

            # Destination
            tx.destination_account.balance = (
                tx.destination_account.balance
                or Decimal("0")
            ) + tx.amount

            tx.destination_account.balance_updated_at = now

            tx.destination_account.save(
                update_fields=[
                    "balance",
                    "balance_updated_at",
                ]
            )

    def _reverse_effect(self, tx):
        """
        Reverse the financial effect of a transaction.

        Used when updating or deleting an existing transaction.
        """

        now = timezone.now()

        if tx.transaction_type == Transaction.TransactionType.INCOME:

            tx.account.balance = (
                tx.account.balance or Decimal("0")
            ) - tx.amount

            tx.account.balance_updated_at = now

            tx.account.save(
                update_fields=[
                    "balance",
                    "balance_updated_at",
                ]
            )

        elif tx.transaction_type == Transaction.TransactionType.EXPENSE:

            tx.account.balance = (
                tx.account.balance or Decimal("0")
            ) + tx.amount

            tx.account.balance_updated_at = now

            tx.account.save(
                update_fields=[
                    "balance",
                    "balance_updated_at",
                ]
            )

        elif tx.transaction_type == Transaction.TransactionType.TRANSFER:

            if tx.destination_account is None:
                raise ValidationError({
                    "code": "INVALID_TRANSFER",
                    "detail": (
                        "Transfer is missing its "
                        "destination account."
                    ),
                })

            # Restore source
            tx.account.balance = (
                tx.account.balance or Decimal("0")
            ) + tx.amount

            tx.account.balance_updated_at = now

            tx.account.save(
                update_fields=[
                    "balance",
                    "balance_updated_at",
                ]
            )

            # Restore destination
            tx.destination_account.balance = (
                tx.destination_account.balance
                or Decimal("0")
            ) - tx.amount

            tx.destination_account.balance_updated_at = now

            tx.destination_account.save(
                update_fields=[
                    "balance",
                    "balance_updated_at",
                ]
            )

    # ============================================================
    # Create
    # ============================================================

    def perform_create(self, serializer):

        with db_transaction.atomic():

            tx = serializer.save()

            accounts_to_lock = [
                tx.account,
                tx.destination_account,
            ]

            list(
                self._lock_accounts(
                    accounts_to_lock
                )
            )

            tx.account.refresh_from_db()

            if tx.destination_account:
                tx.destination_account.refresh_from_db()

            self._apply_effect(tx)

    def create(self, request, *args, **kwargs):

        try:
            serializer = self.get_serializer(
                data=request.data
            )

            serializer.is_valid(
                raise_exception=True
            )

            self.perform_create(serializer)

            return ApiResponse.success(
                message="Transaction created successfully.",
                data=serializer.data,
                status=status.HTTP_201_CREATED,
            )

        except ValidationError as exc:

            return ApiResponse.error(
                message="Unable to create transaction.",
                errors=exc.detail,
                status=status.HTTP_400_BAD_REQUEST,
            )

        except IntegrityError:

            logger.exception(
                "Database integrity error while creating transaction."
            )

            return ApiResponse.error(
                message="Unable to create transaction.",
                errors={
                    "code": "INTEGRITY_ERROR",
                    "detail": (
                        "The transaction could not be saved "
                        "because of a data integrity problem."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception:

            logger.exception(
                "Unexpected error while creating transaction."
            )

            return ApiResponse.error(
                message="Unable to create transaction.",
                errors={
                    "code": "TRANSACTION_CREATE_ERROR",
                    "detail": (
                        "An unexpected error occurred "
                        "while creating the transaction."
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ============================================================
    # Update
    # ============================================================

    def perform_update(self, serializer):

        instance = serializer.instance

        with db_transaction.atomic():

            old_tx = (
                Transaction.objects
                .select_related(
                    "account",
                    "destination_account",
                )
                .select_for_update()
                .get(pk=instance.pk)
            )

            new_account = serializer.validated_data.get(
                "account",
                old_tx.account,
            )

            new_destination = serializer.validated_data.get(
                "destination_account",
                old_tx.destination_account,
            )

            accounts_to_lock = {
                old_tx.account,
                old_tx.destination_account,
                new_account,
                new_destination,
            }

            accounts_to_lock = [
                account
                for account in accounts_to_lock
                if account is not None
            ]

            list(
                self._lock_accounts(
                    accounts_to_lock
                )
            )

            # Refresh every affected account.
            for account in accounts_to_lock:
                account.refresh_from_db()

            # Reverse old transaction.
            old_tx.account.refresh_from_db()

            if old_tx.destination_account:
                old_tx.destination_account.refresh_from_db()

            self._reverse_effect(old_tx)

            # Save new transaction.
            new_tx = serializer.save()

            new_tx.account.refresh_from_db()

            if new_tx.destination_account:
                new_tx.destination_account.refresh_from_db()

            # Apply new transaction.
            self._apply_effect(new_tx)

    def update(self, request, *args, **kwargs):

        partial = kwargs.pop(
            "partial",
            False,
        )

        try:
            instance = self.get_object()

            serializer = self.get_serializer(
                instance,
                data=request.data,
                partial=partial,
            )

            serializer.is_valid(
                raise_exception=True
            )

            self.perform_update(serializer)

            return ApiResponse.success(
                message="Transaction updated successfully.",
                data=serializer.data,
            )

        except ValidationError as exc:

            return ApiResponse.error(
                message="Unable to update transaction.",
                errors=exc.detail,
                status=status.HTTP_400_BAD_REQUEST,
            )

        except IntegrityError:

            logger.exception(
                "Database integrity error while updating transaction."
            )

            return ApiResponse.error(
                message="Unable to update transaction.",
                errors={
                    "code": "INTEGRITY_ERROR",
                    "detail": (
                        "The transaction could not be updated "
                        "because of a data integrity problem."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception:

            logger.exception(
                "Unexpected error while updating transaction."
            )

            return ApiResponse.error(
                message="Unable to update transaction.",
                errors={
                    "code": "TRANSACTION_UPDATE_ERROR",
                    "detail": (
                        "An unexpected error occurred "
                        "while updating the transaction."
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ============================================================
    # Delete
    # ============================================================

    def perform_destroy(self, instance):

        with db_transaction.atomic():

            accounts_to_lock = [
                instance.account,
                instance.destination_account,
            ]

            list(
                self._lock_accounts(
                    accounts_to_lock
                )
            )

            instance.account.refresh_from_db()

            if instance.destination_account:
                instance.destination_account.refresh_from_db()

            self._reverse_effect(instance)

            instance.delete()

    def destroy(self, request, *args, **kwargs):

        try:
            instance = self.get_object()

            self.perform_destroy(instance)

            return ApiResponse.success(
                message="Transaction deleted successfully.",
                status=status.HTTP_200_OK,
            )

        except ValidationError as exc:

            return ApiResponse.error(
                message="Unable to delete transaction.",
                errors=exc.detail,
                status=status.HTTP_400_BAD_REQUEST,
            )

        except IntegrityError:

            logger.exception(
                "Database integrity error while deleting transaction."
            )

            return ApiResponse.error(
                message="Unable to delete transaction.",
                errors={
                    "code": "INTEGRITY_ERROR",
                    "detail": (
                        "The transaction could not be deleted "
                        "because of a data integrity problem."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception:

            logger.exception(
                "Unexpected error while deleting transaction."
            )

            return ApiResponse.error(
                message="Unable to delete transaction.",
                errors={
                    "code": "TRANSACTION_DELETE_ERROR",
                    "detail": (
                        "An unexpected error occurred "
                        "while deleting the transaction."
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    @action(
    detail=False,
    methods=["get"],
    url_path="stats",
    )
    def stats(self, request):
        """
        Return transaction statistics for the authenticated user.

        Search filters are respected, while transaction_type is intentionally
        ignored so that all filter-chip counts remain visible.
        """

        queryset = self.get_queryset()

        # Apply search filtering only.
        search = request.query_params.get("search")

        if search:
            queryset = queryset.filter(
                models.Q(description__icontains=search)
                | models.Q(category__icontains=search)
            )

        stats = queryset.aggregate(
            total=models.Count("id"),
            income=models.Count(
                "id",
                filter=models.Q(
                    transaction_type=Transaction.TransactionType.INCOME
                ),
            ),
            expense=models.Count(
                "id",
                filter=models.Q(
                    transaction_type=Transaction.TransactionType.EXPENSE
                ),
            ),
            transfer=models.Count(
                "id",
                filter=models.Q(
                    transaction_type=Transaction.TransactionType.TRANSFER
                ),
            ),
        )

        return ApiResponse.success(
            message="Transaction statistics retrieved successfully.",
            data=stats,
        )
    from django.shortcuts import get_object_or_404
    from rest_framework.decorators import action

    @action(
        detail=False,
        methods=["get"],
        url_path=r"account/(?P<account_id>\d+)",
    )
    def account_transactions(self, request, account_id=None):
        """
        Return transactions belonging only to the selected account.

        Supports:
        - pagination
        - transaction_type filtering
        - search
        - ordering
        """

        

        # Get account belonging to the authenticated user
        account = get_object_or_404(
            Account,
            id=account_id,
            owner=request.user,
        )

        

        # Get user's transactions and restrict them to this account
        queryset = self.get_queryset().filter(
            account_id=account.id
        )

        

        # Apply transaction_type, search and ordering filters
        queryset = self.filter_queryset(queryset)

        
        # Apply global pagination
        page = self.paginate_queryset(queryset)

        if page is not None:
            

            serializer = self.get_serializer(
                page,
                many=True,
            )

            

            return self.get_paginated_response(
                serializer.data
            )

        

        serializer = self.get_serializer(
            queryset,
            many=True,
        )

        return ApiResponse.success(
            message="Account transactions retrieved successfully.",
            data=serializer.data,
        )