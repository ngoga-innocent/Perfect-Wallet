from decimal import Decimal
import traceback

from django.db.models import Sum
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from Accounts.models import Account
from transactions.models import Transaction
from loans.models import Loan
from reminders.models import FinancialReminder


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        

        try:
            # ============================================================
            # 0. USER / DATE
            # ============================================================

            print("\n--- STEP 0: USER / DATE ---")

            user = request.user
            
            today = timezone.localdate()
            

            # ============================================================
            # 1. ACCOUNTS
            # ============================================================

            print("\n--- STEP 1: ACCOUNTS ---")

            accounts = Account.objects.filter(owner=user)

            

            total_balance = (
                accounts.aggregate(total=Sum("balance"))["total"]
                or Decimal("0.00")
            )

            

            # ============================================================
            # 2. MONTHLY INCOME / EXPENSES
            # ============================================================

            print("\n--- STEP 2: MONTHLY INCOME / EXPENSES ---")

            month_start = today.replace(day=1)

            # ===========================================================
            # We NEED TO UPDATE THIS MONTHLY CALCULATION TO USE THE MONTH A USER IS CURRENTLY IN NOT LAST 30 DAYS
            # ===========================================================

            transactions = Transaction.objects.filter(
                user=user,
                transaction_date__gte=month_start,
                transaction_date__lte=today,
            )

            income = (
                transactions
                .filter(transaction_type="income")
                .aggregate(total=Sum("amount"))["total"]
                or Decimal("0.00")
            )

            expenses = (
                transactions
                .filter(transaction_type="expense")
                .aggregate(total=Sum("amount"))["total"]
                or Decimal("0.00")
            )

            

            net = income - expenses

            

            # ============================================================
            # 3. UPCOMING FINANCIAL REMINDERS
            # ============================================================

            

            upcoming_reminders = (
                FinancialReminder.objects
                .filter(
                    user=user,
                    status="pending",
                    payment_date__gte=today,
                )
                .order_by("payment_date")[:5]
            )

            

            upcoming_events = []

            for reminder in upcoming_reminders:

                

                days_remaining = (
                    reminder.payment_date - today
                ).days

                
                upcoming_events.append({
                    "id": reminder.id,
                    "name": reminder.name,
                    "amount": str(reminder.amount),
                    "payment_date": reminder.payment_date.isoformat(),
                    "days_remaining": days_remaining,
                    "remind_days_before": reminder.remind_days_before,
                    "recurrence": reminder.recurrence,
                    "status": reminder.status,
                })

            

            # ============================================================
            # 4. LOANS
            # ============================================================

            

            loans = Loan.objects.filter(user=user)

            

            

            lent = (
                loans
                .filter(
                    loan_type="lent",
                    status="active",
                )
                .aggregate(total=Sum("remaining_amount"))["total"]
                or Decimal("0.00")
            )

            

            borrowed = (
                loans
                .filter(
                    loan_type="borrowed",
                    status="active",
                )
                .aggregate(total=Sum("remaining_amount"))["total"]
                or Decimal("0.00")
            )

            

            outstanding = lent + borrowed

            

            # ============================================================
            # 5. RECENT TRANSACTIONS
            # ============================================================

            

            recent_transactions = (
                Transaction.objects
                .filter(user=user)
                .select_related(
                    "account",
                    "destination_account",
                )
                .order_by("-created_at")[:5]
            )

            

            recent = []

            for transaction in recent_transactions:

                recent.append({
                    "id": transaction.id,
                    "type": transaction.transaction_type,
                    "amount": str(transaction.amount),
                    "description": transaction.description or "",
                    "date": (
                        transaction.transaction_date.isoformat()
                        if transaction.transaction_date
                        else None
                    ),
                    "account_name": (
                        transaction.account.name
                        if transaction.account
                        else None
                    ),
                    "destination_account_name": (
                        transaction.destination_account.name
                        if transaction.destination_account
                        else None
                    ),
                })

            

            # ============================================================
            # 6. FINANCIAL HEALTH
            # ============================================================

            

            if income > 0:

             

                expense_ratio = (
                    (expenses / income) * Decimal("100")
                ).quantize(Decimal("0.01"))

            else:

                

                expense_ratio = Decimal("0.00")

            

            # ============================================================
            # 7. RESPONSE
            # ============================================================

            

            response_data = {
                "balance": {
                    "total": str(total_balance),
                    "currency": "RWF",
                },

                "summary": {
                    "income": str(income),
                    "expenses": str(expenses),
                    "net": str(net),
                },

                "accounts": {
                    "count": accounts.count(),
                    "total_balance": str(total_balance),
                },

                "loans": {
                    "lent": str(lent),
                    "borrowed": str(borrowed),
                    "outstanding": str(outstanding),
                },

                "upcoming_events": upcoming_events,

                "recent_transactions": recent,

                "financial_health": {
                    "income": str(income),
                    "expenses": str(expenses),
                    "savings": str(net),
                    "expense_ratio": str(expense_ratio),
                },
            }

           

            return Response(response_data)

        except Exception as e:

            print("\n" + "=" * 80)
            print("DASHBOARD DEBUG ERROR")
            print("=" * 80)

            print("ERROR TYPE:", type(e))
            print("ERROR:", str(e))
            print("ERROR REPR:", repr(e))

            print("\nFULL TRACEBACK:")
            traceback.print_exc()

            print("=" * 80)

            return Response(
                {
                    "success": False,
                    "message": "Dashboard error",
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                status=500,
            )