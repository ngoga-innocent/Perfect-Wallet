from rest_framework import filters, status, viewsets
from rest_framework.permissions import IsAuthenticated

from common.responses import ApiResponse
from rest_framework.decorators import action
from .models import Loan
from .serializers import LoanSerializer,LoanPaymentSerializer
from .services import LoanService
from rest_framework.exceptions import ValidationError

class LoanViewSet(viewsets.ModelViewSet):

    serializer_class = LoanSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    search_fields = [
        "person",
        "description",
    ]

    ordering_fields = [
        "created_at",
        "updated_at",
        "principal_amount",
        "remaining_amount",
        "payment_date",
    ]

    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = Loan.objects.filter(
            user=self.request.user
        ).select_related(
            "account"
        )

        loan_type = self.request.query_params.get("loan_type")

        if loan_type:
            queryset = queryset.filter(
                loan_type=loan_type
            )

        loan_status = self.request.query_params.get("status")

        if loan_status:
            queryset = queryset.filter(
                status=loan_status
            )

        currency = self.request.query_params.get("currency")

        if currency:
            queryset = queryset.filter(
                currency=currency.upper()
            )

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(
            self.get_queryset()
        )

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
            message="Loans retrieved successfully.",
            data=serializer.data,
            status=status.HTTP_200_OK,
        )

    def retrieve(self, request, *args, **kwargs):
        loan = self.get_object()

        serializer = self.get_serializer(loan)

        return ApiResponse.success(
            message="Loan retrieved successfully.",
            data=serializer.data,
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(
            data=request.data
        )

        if not serializer.is_valid():
            return ApiResponse.error(
                message="Please correct the errors and try again.",
                errors=serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            loan = LoanService.create_loan(
                user=request.user,
                validated_data=serializer.validated_data,
            )

        except Exception as exc:
            return ApiResponse.error(
                message=str(exc),
                status=status.HTTP_400_BAD_REQUEST,
            )

        return ApiResponse.success(
            message="Loan created successfully.",
            data=self.get_serializer(loan).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):

        loan = self.get_object()

        serializer = self.get_serializer(
            loan,
            data=request.data,
        )

        if not serializer.is_valid():
            return ApiResponse.error(
                message="Please correct the errors and try again.",
                errors=serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            loan = LoanService.update_loan(
                user=request.user,
                loan=loan,
                validated_data=serializer.validated_data,
            )

        except Exception as exc:
            return ApiResponse.error(
                message=str(exc),
                status=status.HTTP_400_BAD_REQUEST,
            )

        return ApiResponse.success(
            message="Loan updated successfully.",
            data=self.get_serializer(loan).data,
            status=status.HTTP_200_OK,
        )

    def partial_update(self, request, *args, **kwargs):
        loan = self.get_object()

        # print("REQUEST DATA:", request.data)

        serializer = self.get_serializer(
            loan,
            data=request.data,
            partial=True,
        )

        valid = serializer.is_valid()

        # print("IS VALID:", valid)
        # print("ERRORS:", serializer.errors)

        if not valid:
            return ApiResponse.error(
                message="Please correct the errors and try again.",
                errors=serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        # print("VALIDATED DATA:", serializer.validated_data)

        try:
            loan = LoanService.update_loan(
                user=request.user,
                loan=loan,
                validated_data=serializer.validated_data,
            )

        except Exception as exc:
            print("UPDATE ERROR:", repr(exc))

            return ApiResponse.error(
                message=str(exc),
                errors={"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return ApiResponse.success(
            message="Loan updated successfully.",
            data=self.get_serializer(loan).data,
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):

        loan = self.get_object()

        try:
            LoanService.delete_loan(
                user=request.user,
                loan=loan,
            )

        except Exception as exc:
            return ApiResponse.error(
                message=str(exc),
                status=status.HTTP_400_BAD_REQUEST,
            )

        return ApiResponse.success(
            message="Loan deleted successfully.",
            data={},
            status=status.HTTP_200_OK,
        )
    @action(
    detail=True,
    methods=["post"],
    url_path="payment",
    )
    def record_payment(self, request, *args, **kwargs):

        print("\n")
        print("=" * 80)
        print("LOAN PAYMENT DEBUG START")
        print("=" * 80)

        print("USER:", request.user)
        print("USER ID:", request.user.id)

        print("LOAN PK:", kwargs.get("pk"))

        print("REQUEST DATA:", request.data)
        print("REQUEST DATA TYPE:", type(request.data))

        try:

            # --------------------------------------------------
            # 1. Get loan
            # --------------------------------------------------

            print("\n--- STEP 1: GET LOAN ---")

            loan = self.get_object()

            print("LOAN FOUND:", loan)
            print("LOAN ID:", loan.id)
            print("LOAN PERSON:", loan.person)
            print("LOAN TYPE:", loan.loan_type)
            print("LOAN PRINCIPAL:", loan.principal_amount)
            print("LOAN PAID:", loan.paid_amount)
            print("LOAN REMAINING:", loan.remaining_amount)
            print("LOAN STATUS:", loan.status)
            print("LOAN CURRENCY:", loan.currency)
            print("LOAN ACCOUNT:", loan.account_id)

            # --------------------------------------------------
            # 2. Serializer
            # --------------------------------------------------

            print("\n--- STEP 2: SERIALIZER ---")

            serializer = LoanPaymentSerializer(
                data=request.data,
                context={
                    "request": request,
                },
            )

            print("SERIALIZER CREATED")

            is_valid = serializer.is_valid()

            print("SERIALIZER VALID:", is_valid)
            print("SERIALIZER ERRORS:", serializer.errors)

            if not is_valid:

                print("SERIALIZER VALIDATION FAILED")

                return ApiResponse.error(
                    message="Please correct the errors and try again.",
                    errors=serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST,
                )

            print("VALIDATED DATA:", serializer.validated_data)

            # --------------------------------------------------
            # 3. Extract values
            # --------------------------------------------------

            print("\n--- STEP 3: EXTRACT DATA ---")

            amount = serializer.validated_data["amount"]
            account = serializer.validated_data["account"]

            payment_date = serializer.validated_data.get(
                "payment_date"
            )

            description = serializer.validated_data.get(
                "description",
                "",
            )

            print("AMOUNT:", amount)
            print("AMOUNT TYPE:", type(amount))

            print("ACCOUNT:", account)
            print("ACCOUNT ID:", account.id)

            print("ACCOUNT OWNER:", account.owner_id)
            print("ACCOUNT BALANCE:", account.balance)
            print("ACCOUNT CURRENCY:", account.currency)
            print("ACCOUNT ACTIVE:", account.is_active)

            print("PAYMENT DATE:", payment_date)
            print("DESCRIPTION:", description)

            # --------------------------------------------------
            # 4. Call service
            # --------------------------------------------------

            print("\n--- STEP 4: CALL LOAN SERVICE ---")

            loan = LoanService.record_payment(
                user=request.user,
                loan=loan,
                amount=amount,
                account=account,
                payment_date=payment_date,
                description=description,
            )

            print("SERVICE COMPLETED SUCCESSFULLY")

            # --------------------------------------------------
            # 5. Check resulting loan
            # --------------------------------------------------

            print("\n--- STEP 5: UPDATED LOAN ---")

            print("ID:", loan.id)
            print("PRINCIPAL:", loan.principal_amount)
            print("PAID:", loan.paid_amount)
            print("REMAINING:", loan.remaining_amount)
            print("STATUS:", loan.status)

            # --------------------------------------------------
            # 6. Serialize response
            # --------------------------------------------------

            print("\n--- STEP 6: RESPONSE SERIALIZATION ---")

            response_data = self.get_serializer(loan).data

            print("RESPONSE DATA:", response_data)

            print("\n")
            print("=" * 80)
            print("LOAN PAYMENT DEBUG SUCCESS")
            print("=" * 80)

            return ApiResponse.success(
                message="Loan payment recorded successfully.",
                data=response_data,
                status=status.HTTP_200_OK,
            )

        except ValidationError as exc:

            print("\n")
            print("=" * 80)
            print("LOAN PAYMENT VALIDATION ERROR")
            print("=" * 80)

            print("ERROR:", repr(exc))
            print("DETAIL:", getattr(exc, "detail", None))

            return ApiResponse.error(
                message="Unable to record loan payment.",
                errors=getattr(
                    exc,
                    "detail",
                    {"detail": str(exc)},
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as exc:

            print("\n")
            print("=" * 80)
            print("LOAN PAYMENT UNEXPECTED ERROR")
            print("=" * 80)

            print("ERROR TYPE:", type(exc))
            print("ERROR:", repr(exc))

            import traceback

            traceback.print_exc()

            print("=" * 80)
            print("LOAN PAYMENT DEBUG END")
            print("=" * 80)

            return ApiResponse.error(
                message="An unexpected error occurred while recording the payment.",
                errors={
                    "detail": str(exc),
                    "type": type(exc).__name__,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )