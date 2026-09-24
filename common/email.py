
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

class EmailService:

    @staticmethod
    def send(
        *,
        subject,
        template,
        context=None,
        recipient,
        text_content=None,
        from_email=None,
    ):
        """
        Generic email sender.

        All WalletFlow emails should eventually go
        through this method.
        """

        context = context or {}

        html_content = render_to_string(
            template,
            context,
        )

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content or "",
            from_email=(
                from_email
                or settings.DEFAULT_FROM_EMAIL
            ),
            to=[recipient],
        )

        email.attach_alternative(
            html_content,
            "text/html",
        )

        email.send(
            fail_silently=False
        )

    # -------------------------------------------------
    # OTP EMAIL
    # -------------------------------------------------

    @staticmethod
    def send_otp(
        *,
        user,
        otp,
        purpose,
        expires_minutes=5,
    ):

        email_config = {
            "password_reset": {
                "subject": "Reset your WalletFlow password",
                "title": "Reset your password",
                "action": "password reset",
            },

            "pin_reset": {
                "subject": "Reset your WalletFlow PIN",
                "title": "Reset your Wallet PIN",
                "action": "PIN reset",
            },

            "email_verification": {
                "subject": "Verify your WalletFlow email",
                "title": "Verify your email",
                "action": "email verification",
            },
        }

        config = email_config.get(
            purpose
        )

        if not config:
            raise ValueError(
                f"Unsupported OTP purpose: {purpose}"
            )

        context = {
            "user": user,
            "otp": otp,
            "title": config["title"],
            "action": config["action"],
            "expires_minutes": expires_minutes,
        }

        text_content = (
            f"Your WalletFlow verification code is "
            f"{otp}. "
            f"It expires in "
            f"{expires_minutes} minutes."
        )

        EmailService.send(
            subject=config["subject"],
            template="emails/otp/verification.html",
            context=context,
            recipient=user.email,
            text_content=text_content,
        )

    # -------------------------------------------------
    # WELCOME EMAIL
    # -------------------------------------------------

    @staticmethod
    def send_welcome(
        *,
        user,
    ):

        subject = "Welcome to WalletFlow"

        context = {
            "user": user,
        }

        text_content = (
            f"Welcome to WalletFlow, "
            f"{user.first_name or user.email}."
        )

        EmailService.send(
            subject=subject,
            template="emails/welcome.html",
            context=context,
            recipient=user.email,
            text_content=text_content,
        )

    # -------------------------------------------------
    # PASSWORD CHANGED
    # -------------------------------------------------

    @staticmethod
    def send_password_changed(
        *,
        user,
    ):

        subject = "Your WalletFlow password was changed"

        context = {
            "user": user,
        }

        text_content = (
            "Your WalletFlow password was successfully changed."
        )

        EmailService.send(
            subject=subject,
            template="emails/password_changed.html",
            context=context,
            recipient=user.email,
            text_content=text_content,
        )

    # -------------------------------------------------
    # PIN CHANGED
    # -------------------------------------------------

    @staticmethod
    def send_pin_changed(
        *,
        user,
    ):

        subject = "Your WalletFlow PIN was changed"

        context = {
            "user": user,
        }

        text_content = (
            "Your WalletFlow PIN was successfully changed."
        )

        EmailService.send(
            subject=subject,
            template="emails/pin_changed.html",
            context=context,
            recipient=user.email,
            text_content=text_content,
        )

    # -------------------------------------------------
    # SECURITY ALERT
    # -------------------------------------------------

    @staticmethod
    def send_security_alert(
        *,
        user,
        title,
        message,
    ):

        subject = f"WalletFlow security alert: {title}"

        context = {
            "user": user,
            "title": title,
            "message": message,
        }

        text_content = (
            f"WalletFlow security alert: {title}\n\n"
            f"{message}"
        )

        EmailService.send(
            subject=subject,
            template="emails/security_alert.html",
            context=context,
            recipient=user.email,
            text_content=text_content,
        )

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone


def send_financial_reminder_email(
    reminder,
    reminder_url=None,
):
    today = timezone.localdate()

    days_remaining = (
        reminder.payment_date - today
    ).days

    user_name = (
        reminder.user.first_name
        or reminder.user.username
        or "there"
    )

    subject = (
        f"Payment Reminder: {reminder.name}"
    )

    context = {
        "subject": subject,
        "user_name": user_name,
        "reminder": reminder,
        "amount": f"{reminder.amount:,.2f} RWF",
        "payment_date": reminder.payment_date.strftime(
            "%d %B %Y"
        ),
        "days_remaining": days_remaining,
        "reminder_url": reminder_url,
    }

    html_content = render_to_string(
        "emails/financial_reminder.html",
        context,
    )

    text_content = (
        f"Hello {user_name},\n\n"
        f"This is a reminder about your upcoming payment.\n\n"
        f"Reminder: {reminder.name}\n"
        f"Amount: {context['amount']}\n"
        f"Payment date: {context['payment_date']}\n\n"
    )

    if days_remaining == 0:
        text_content += (
            "This payment is due today."
        )
    elif days_remaining == 1:
        text_content += (
            "This payment is due tomorrow."
        )
    else:
        text_content += (
            f"This payment is due in "
            f"{days_remaining} days."
        )

    if reminder_url:
        text_content += (
            f"\n\nView your reminder: "
            f"{reminder_url}"
        )

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[reminder.user.email],
    )

    email.attach_alternative(
        html_content,
        "text/html",
    )

    email.send(
        fail_silently=False,
    )