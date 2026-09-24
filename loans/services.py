from decimal import Decimal

from django.db import transaction as db_transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from Accounts.models import Account
from transactions.models import Transaction

from .models import Loan


class LoanService:

    @staticmethod
    def _validate_account(user, account):
        if account.owner_id != user.id:
            raise ValidationError({
                "account": "The selected account does not belong to you."
            })

        if not account.is_active:
            raise ValidationError({
                "account": "The selected account is not active."
            })

        return account

    @staticmethod
    def _apply_creation_balance(account, loan_type, amount):
        """
        LENT     -> money leaves our account
        BORROWED -> money enters our account
        """

        if loan_type == Loan.LoanType.LENT:
            if account.balance < amount:
                raise ValidationError({
                    "account": (
                        f"Insufficient balance in account "
                        f"'{account.name}'. "
                        f"Available balance: {account.balance}, "
                        f"requested: {amount}."
                    )
                })

            account.balance -= amount

        elif loan_type == Loan.LoanType.BORROWED:
            account.balance += amount

    @staticmethod
    def _apply_payment_balance(account, loan_type, amount):
        """
        LENT loan repayment:
            money comes back -> account increases

        BORROWED loan repayment:
            money leaves account -> account decreases
        """

        if loan_type == Loan.LoanType.LENT:
            account.balance += amount

        elif loan_type == Loan.LoanType.BORROWED:
            if account.balance < amount:
                raise ValidationError({
                    "account": (
                        f"Insufficient balance in account "
                        f"'{account.name}' to repay this loan."
                    )
                })

            account.balance -= amount

    @staticmethod
    @db_transaction.atomic
    def create_loan(*, user, validated_data):

        account = validated_data["account"]

        LoanService._validate_account(
            user,
            account,
        )

        principal = validated_data["principal_amount"]
        loan_type = validated_data["loan_type"]

        # Make sure account currency matches loan currency
        currency = validated_data.get(
            "currency",
            account.currency,
        )

        if account.currency.upper() != currency.upper():
            raise ValidationError({
                "currency": (
                    f"Loan currency {currency} does not match "
                    f"account currency {account.currency}."
                )
            })

        # Update account balance
        LoanService._apply_creation_balance(
            account,
            loan_type,
            principal,
        )

        account.balance_updated_at = timezone.now()
        account.save(
            update_fields=[
                "balance",
                "balance_updated_at",
                "updated_at",
            ]
        )

        # Create loan
        loan = Loan.objects.create(
            user=user,
            remaining_amount=principal,
            **validated_data,
        )

        # Create transaction
        if loan_type == Loan.LoanType.LENT:
            description = (
                f"Loan lent to {loan.person}"
            )
        else:
            description = (
                f"Money borrowed from {loan.person}"
            )

        Transaction.objects.create(
            user=user,
            account=account,
            loan=loan,
            transaction_type=Transaction.TransactionType.LOAN,
            amount=principal,
            description=description,
            category="loan",
            transaction_date=timezone.now(),
        )

        return loan

    @staticmethod
    @db_transaction.atomic
    def delete_loan(*, user, loan):

        if loan.user_id != user.id:
            raise ValidationError(
                "You do not have permission to delete this loan."
            )

        account = loan.account

        transactions = list(
            loan.transactions.select_for_update()
        )

        # Reverse every financial transaction associated
        # with this loan before deleting it.
        for txn in transactions:

            if txn.transaction_type == Transaction.TransactionType.LOAN:

                if txn.loan_id != loan.id:
                    continue

                # Determine whether this transaction was an
                # initial loan or repayment.
                #
                # We will use the description/category convention
                # for now. This can later be replaced by a
                # transaction direction field.
                if txn.description.startswith("Loan lent to"):
                    account.balance += txn.amount

                elif txn.description.startswith("Money borrowed from"):
                    account.balance -= txn.amount

                elif txn.description.startswith("Repayment received"):
                    account.balance -= txn.amount

                elif txn.description.startswith("Loan repayment"):
                    account.balance += txn.amount

        if account.balance < 0:
            raise ValidationError({
                "account": (
                    "Deleting this loan would result in a negative "
                    "account balance."
                )
            })

        account.balance_updated_at = timezone.now()

        account.save(
            update_fields=[
                "balance",
                "balance_updated_at",
                "updated_at",
            ]
        )

        # Transaction.loan uses PROTECT, so delete the transactions
        # first.
        loan.transactions.all().delete()

        loan.delete()
    @staticmethod
    @db_transaction.atomic
    def update_loan(*, user, loan, validated_data):

        if loan.user_id != user.id:
            raise ValidationError(
                "You do not have permission to update this loan."
            )

        # ---------------------------------------------------------
        # 1. Check whether this loan already has repayments
        # ---------------------------------------------------------

        has_payments = loan.transactions.filter(
            loan_transaction_type=Transaction.LoanTransactionType.REPAYMENT
        ).exists()

        protected_fields = {
            "account",
            "loan_type",
            "principal_amount",
            "currency",
        }

        if has_payments:
            changed = protected_fields.intersection(
                validated_data.keys()
            )

            if changed:
                raise ValidationError({
                    field: (
                        "This field cannot be changed after "
                        "loan payments have been recorded."
                    )
                    for field in changed
                })

        # ---------------------------------------------------------
        # 2. Separate financial fields from normal fields
        # ---------------------------------------------------------

        financial_fields = {
            "account",
            "loan_type",
            "principal_amount",
            "currency",
        }

        financial_changed = bool(
            financial_fields.intersection(validated_data.keys())
        )

        # No financial changes?
        # Just update normal loan information.
        if not financial_changed:

            for field, value in validated_data.items():
                setattr(loan, field, value)

            loan.save()

            return loan

        # ---------------------------------------------------------
        # 3. Existing values
        # ---------------------------------------------------------

        old_account = loan.account
        old_loan_type = loan.loan_type
        old_principal = loan.principal_amount
        old_currency = loan.currency

        # New values, falling back to existing values
        new_account = validated_data.get(
            "account",
            old_account,
        )

        new_loan_type = validated_data.get(
            "loan_type",
            old_loan_type,
        )

        new_principal = validated_data.get(
            "principal_amount",
            old_principal,
        )

        new_currency = validated_data.get(
            "currency",
            old_currency,
        )

        # ---------------------------------------------------------
        # 4. Validate the new account
        # ---------------------------------------------------------

        LoanService._validate_account(
            user,
            new_account,
        )

        # Account currency must match loan currency
        if new_account.currency.upper() != new_currency.upper():
            raise ValidationError({
                "currency": (
                    f"Loan currency {new_currency} does not match "
                    f"account currency {new_account.currency}."
                )
            })

        # ---------------------------------------------------------
        # 5. Find the original loan transaction
        # ---------------------------------------------------------

        loan_transaction = loan.transactions.filter(
            transaction_type=Transaction.TransactionType.LOAN
        ).first()

        if not loan_transaction:
            raise ValidationError({
                "transaction": (
                    "The original loan transaction could not be found."
                )
            })

        # ---------------------------------------------------------
        # 6. Reverse the OLD financial effect
        # ---------------------------------------------------------

        if old_loan_type == Loan.LoanType.LENT:

            # Originally money left our account.
            # Put it back.
            old_account.balance += old_principal

        elif old_loan_type == Loan.LoanType.BORROWED:

            # Originally money entered our account.
            # Remove it.
            old_account.balance -= old_principal

            if old_account.balance < 0:
                raise ValidationError({
                    "account": (
                        f"Cannot reverse the original borrowed amount "
                        f"from account '{old_account.name}'."
                    )
                })

        old_account.balance_updated_at = timezone.now()

        old_account.save(
            update_fields=[
                "balance",
                "balance_updated_at",
                "updated_at",
            ]
        )

        # ---------------------------------------------------------
        # 7. Apply the NEW financial effect
        # ---------------------------------------------------------

        LoanService._apply_creation_balance(
            new_account,
            new_loan_type,
            new_principal,
        )

        new_account.balance_updated_at = timezone.now()

        new_account.save(
            update_fields=[
                "balance",
                "balance_updated_at",
                "updated_at",
            ]
        )

        # ---------------------------------------------------------
        # 8. Update Loan
        # ---------------------------------------------------------

        for field, value in validated_data.items():
            setattr(loan, field, value)

        # No payments exist, so remaining equals principal.
        loan.remaining_amount = new_principal

        loan.save()

        # ---------------------------------------------------------
        # 9. Update the original transaction
        # ---------------------------------------------------------

        loan_transaction.account = new_account
        loan_transaction.amount = new_principal

        if new_loan_type == Loan.LoanType.LENT:

            loan_transaction.description = (
                f"Loan lent to {loan.person}"
            )

        else:

            loan_transaction.description = (
                f"Money borrowed from {loan.person}"
            )

        loan_transaction.save(
            update_fields=[
                "account",
                "amount",
                "description",
                "updated_at",
            ]
        )

        return loan
    @staticmethod
    @db_transaction.atomic
    def record_payment(
        *,
        user,
        loan,
        amount,
        account,
        payment_date=None,
        description="",
    ):

        # ---------------------------------------------------------
        # 1. Verify loan ownership
        # ---------------------------------------------------------
       
        if loan.user_id != user.id:
            raise ValidationError(
                "You do not have permission to make a payment "
                "on this loan."
            )

        # ---------------------------------------------------------
        # 2. Loan must still be active
        # ---------------------------------------------------------

        

        if loan.status == Loan.Status.PAID:
            print("LOAN IS ALREADY PAID")
            raise ValidationError(
                "This loan has already been fully paid."
            )

        print("STATUS CHECK PASSED")


        # ---------------------------------------------------------
        # 3. Validate account
        # ---------------------------------------------------------

        

        LoanService._validate_account(
            user,
            account,
        )

        


        # ---------------------------------------------------------
        # 4. Validate currency
        # ---------------------------------------------------------


        account_currency = account.currency.upper()
        loan_currency = loan.currency.upper()

   

        if account_currency != loan_currency:
            print("CURRENCY MISMATCH")

            raise ValidationError({
                "currency": (
                    f"Payment account currency {account.currency} "
                    f"does not match loan currency {loan.currency}."
                )
            })

        

        # ---------------------------------------------------------
        # 5. Validate payment amount
        # ---------------------------------------------------------

        

        if amount <= Decimal("0"):
            

            raise ValidationError({
                "amount": "Payment amount must be greater than zero."
            })

        print("AMOUNT > 0 PASSED")

        if amount > loan.remaining_amount:
            

            raise ValidationError({
                "amount": (
                    "Payment amount cannot be greater than the "
                    f"remaining loan balance of {loan.remaining_amount}."
                )
            })

       


        # ---------------------------------------------------------
        # 6. Update account balance
        # ---------------------------------------------------------

        

        LoanService._apply_payment_balance(
            account,
            loan.loan_type,
            amount,
        )

        

        account.balance_updated_at = timezone.now()

        

        account.save(
            update_fields=[
                "balance",
                "balance_updated_at",
                "updated_at",
            ]
        )

        print("ACCOUNT SAVED SUCCESSFULLY")


       # ---------------------------------------------------------
        # 7. Update loan remaining amount
        # ---------------------------------------------------------

        

        loan.remaining_amount -= amount

        # Prevent tiny decimal precision issues
        if loan.remaining_amount < Decimal("0.00"):
            loan.remaining_amount = Decimal("0.00")

        


        # ---------------------------------------------------------
        # 8. Update loan status
        # ---------------------------------------------------------

       

        if loan.remaining_amount == Decimal("0.00"):
            loan.status = Loan.Status.PAID
        else:
            loan.status = Loan.Status.ACTIVE

       

        if payment_date:
            loan.payment_date = payment_date

        loan.save(
            update_fields=[
                "remaining_amount",
                "status",
                "payment_date",
                "updated_at",
            ]
        )



        # ---------------------------------------------------------
        # 9. Create repayment transaction
        # ---------------------------------------------------------


        if description:
            transaction_description = description

        elif loan.loan_type == Loan.LoanType.LENT:
            transaction_description = (
                f"Repayment received from {loan.person}"
            )

        else:
            transaction_description = (
                f"Loan repayment to {loan.person}"
            )

        

        

        Transaction.objects.create(
            user=user,
            account=account,
            loan=loan,
            transaction_type=Transaction.TransactionType.LOAN,
            loan_transaction_type=(
                Transaction.LoanTransactionType.REPAYMENT
            ),
            amount=amount,
            description=transaction_description,
            category="loan",
            transaction_date=(
                payment_date
                or timezone.now().date()
            ),
        )

        print("TRANSACTION CREATED SUCCESSFULLY")

        return loan