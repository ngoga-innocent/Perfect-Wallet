import requests
from django.utils import timezone


from common.email import send_financial_reminder_email

from datetime import timedelta

from django.utils import timezone

from ..models import (
    FinancialReminder,
    ReminderNotification,
    UserDevice,
)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def send_expo_push_notification(
    *,
    token,
    title,
    body,
    data=None,
):
    payload = {
        "to": token,
        "sound": "default",
        "title": title,
        "body": body,
        "data": data or {},
    }

    response = requests.post(
        EXPO_PUSH_URL,
        json=payload,
        timeout=10,
    )

    response.raise_for_status()

    result = response.json()

    # Expo normally returns a response containing "data".
    tickets = result.get("data", [])

    if not tickets:
        raise RuntimeError(
            "Expo returned an empty push notification response."
        )

    ticket = tickets[0]

    if ticket.get("status") != "ok":
        error = ticket.get("details", {}).get(
            "error",
            "Unknown Expo push error.",
        )

        raise RuntimeError(
            f"Expo push notification failed: {error}"
        )

    return result



def get_notification_message(reminder):
    today = timezone.localdate()

    days_remaining = (
        reminder.payment_date - today
    ).days

    if days_remaining < 0:
        return (
            f"{reminder.name} was due "
            f"{abs(days_remaining)} days ago."
        )

    if days_remaining == 0:
        message = (
            f"{reminder.name} of "
            f"{reminder.amount:,.2f} is due today."
        )

    elif days_remaining == 1:
        message = (
            f"{reminder.name} of "
            f"{reminder.amount:,.2f} is due tomorrow."
        )

    else:
        message = (
            f"{reminder.name} of "
            f"{reminder.amount:,.2f} is due in "
            f"{days_remaining} days."
        )

    return message


def send_financial_reminder_notifications(
    reminder,
    notification_date=None,
):
    """
    Send email and push notifications for one reminder.
    """

    if reminder.status != FinancialReminder.Status.PENDING:
        return {
            "sent": False,
            "reason": "Reminder is not pending.",
        }

    today = (
        notification_date
        or timezone.localdate()
    )

    reminder_date = reminder.reminder_date
    payment_date = reminder.payment_date

    # Notification window has not started.
    if today < reminder_date:
        return {
            "sent": False,
            "reason": "Notification window has not started.",
        }

    # Payment date has passed.
    if today > payment_date:
        return {
            "sent": False,
            "reason": "Payment date has passed.",
        }

    results = {
        "email": False,
        "push": False,
    }

    errors = {
        "email": None,
        "push": None,
    }

    # =================================================
    # EMAIL
    # =================================================

    email_already_sent = (
        ReminderNotification.objects.filter(
            reminder=reminder,
            notification_date=today,
            channel=ReminderNotification.Channel.EMAIL,
        ).exists()
    )

    if not email_already_sent:

        user_email = reminder.user.email

        if user_email:

            try:

                send_financial_reminder_email(
                    reminder=reminder,
                )

                ReminderNotification.objects.create(
                    reminder=reminder,
                    user=reminder.user,
                    notification_date=today,
                    channel=(
                        ReminderNotification.Channel.EMAIL
                    ),
                )

                results["email"] = True

            except Exception as exc:

                errors["email"] = str(exc)

    # =================================================
    # PUSH
    # =================================================

    push_already_sent = (
        ReminderNotification.objects.filter(
            reminder=reminder,
            notification_date=today,
            channel=ReminderNotification.Channel.PUSH,
        ).exists()
    )

    if not push_already_sent:

        devices = UserDevice.objects.filter(
            user=reminder.user,
            is_active=True,
        )

        if devices.exists():

            push_success = False

            for device in devices:

                try:
                    send_expo_push_notification(
                        token=device.expo_push_token,
                        title="Perfect Wallet Reminder",
                        body=get_notification_message(reminder),
                        data={
                            "type": "financial_reminder",
                            "reminder_id": reminder.id,
                        },
                    )

                    push_success = True

                except Exception as exc:
                    errors["push"] = str(exc)

                if push_success:

                    ReminderNotification.objects.create(
                        reminder=reminder,
                        user=reminder.user,
                        notification_date=today,
                        channel=(
                            ReminderNotification.Channel.PUSH
                        ),
                    )

                    results["push"] = True

        return {
            "sent": (
                results["email"]
                or results["push"]
            ),
            "results": results,
            "errors": errors,
        }


def send_todays_financial_reminders():
    """
    Find all pending reminders whose notification
    window includes today and send notifications.
    """

    today = timezone.localdate()

    reminders = (
        FinancialReminder.objects
        .filter(
            status=FinancialReminder.Status.PENDING,
            payment_date__gte=today,
            payment_date__lte=today + timedelta(days=365),
        )
        .select_related("user")
    )

    results = []

    for reminder in reminders:

        # Skip reminders whose notification window
        # has not started yet.
        if today < reminder.reminder_date:
            continue

        result = send_financial_reminder_notifications(
            reminder=reminder,
            notification_date=today,
        )

        results.append({
            "reminder_id": reminder.id,
            "name": reminder.name,
            "result": result,
        })

    return results