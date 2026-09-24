from django.db import transaction as db_transaction

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .models import FinancialReminder
from .serializers import FinancialReminderSerializer


class FinancialReminderViewSet(ModelViewSet):

    serializer_class = FinancialReminderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            FinancialReminder.objects
            .filter(user=self.request.user)
            .order_by("payment_date", "-created_at")
        )

    def perform_create(self, serializer):
        serializer.save(
            user=self.request.user
        )

    def perform_update(self, serializer):
        serializer.save()

    @action(
        detail=True,
        methods=["post"],
        url_path="complete",
    )
    @db_transaction.atomic
    def complete(self, request, *args, **kwargs):

        reminder = self.get_object()

        if reminder.status == (
            FinancialReminder.Status.COMPLETED
        ):
            raise ValidationError(
                "This reminder has already been completed."
            )

        reminder.status = (
            FinancialReminder.Status.COMPLETED
        )

        reminder.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        # Recurring reminder handling will go here.
        # We will implement it after the basic CRUD
        # is confirmed working.

        serializer = self.get_serializer(reminder)

        return Response(
            {
                "success": True,
                "message": "Reminder marked as completed.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
from django.utils import timezone

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import UserDevice
from .serializers import UserDeviceSerializer


class RegisterDeviceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UserDeviceSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "message": "Invalid device information.",
                    "data": None,
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        expo_push_token = serializer.validated_data["expo_push_token"]
        platform = serializer.validated_data.get("platform", "unknown")
        device_name = serializer.validated_data.get("device_name")

        device, created = UserDevice.objects.update_or_create(
            expo_push_token=expo_push_token,
            defaults={
                "user": request.user,
                "platform": platform,
                "device_name": device_name,
                "is_active": True,
                "last_registered_at": timezone.now(),
            },
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Device registered successfully."
                    if created
                    else "Device registration updated successfully."
                ),
                "data": UserDeviceSerializer(device).data,
                "errors": None,
            },
            status=(
                status.HTTP_201_CREATED
                if created
                else status.HTTP_200_OK
            ),
        )