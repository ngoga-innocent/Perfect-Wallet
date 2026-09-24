import secrets

from datetime import timedelta

from django.contrib.auth.hashers import (
    make_password,
    check_password,
)

from django.utils import timezone

from authentication.models import OTPVerification


class OTPService:

    OTP_LENGTH = 6
    OTP_EXPIRY_MINUTES = 5
    MAX_ATTEMPTS = 5

    @staticmethod
    def generate_otp():

        return "".join(
            str(secrets.randbelow(10))
            for _ in range(OTPService.OTP_LENGTH)
        )

    @staticmethod
    def create(
        *,
        user,
        purpose,
    ):

        # Invalidate previous active OTPs
        OTPVerification.objects.filter(
            user=user,
            purpose=purpose,
            verified=False,
        ).update(
            verified=True
        )

        otp = OTPService.generate_otp()

        otp_record = OTPVerification.objects.create(
            user=user,
            purpose=purpose,
            otp_hash=make_password(otp),
            expires_at=timezone.now()
            + timedelta(
                minutes=OTPService.OTP_EXPIRY_MINUTES
            ),
            max_attempts=OTPService.MAX_ATTEMPTS,
        )

        return otp_record, otp

    @staticmethod
    def verify(
        *,
        user,
        purpose,
        otp,
    ):

        otp_record = (
            OTPVerification.objects
            .filter(
                user=user,
                purpose=purpose,
                verified=False,
            )
            .order_by("-created_at")
            .first()
        )

        if not otp_record:
            return False, "Invalid or expired OTP."

        if timezone.now() > otp_record.expires_at:

            otp_record.verified = True
            otp_record.save(
                update_fields=["verified"]
            )

            return False, "OTP has expired."

        if otp_record.attempts >= otp_record.max_attempts:

            otp_record.verified = True
            otp_record.save(
                update_fields=["verified"]
            )

            return False, "Too many verification attempts."

        otp_record.attempts += 1

        if not check_password(
            otp,
            otp_record.otp_hash,
        ):

            otp_record.save(
                update_fields=["attempts"]
            )

            return False, "Invalid OTP."

        otp_record.verified = True

        otp_record.save(
            update_fields=[
                "attempts",
                "verified",
            ]
        )

        return True, None
    @staticmethod
    def verify_with_record(
        *,
        user,
        purpose,
        otp,
    ):
        otp_record = (
            OTPVerification.objects
            .filter(
                user=user,
                purpose=purpose,
                verified=False,
            )
            .order_by("-created_at")
            .first()
        )

        # -----------------------------------------
        # No active OTP
        # -----------------------------------------

        if not otp_record:
            return (
                False,
                "Invalid or expired OTP.",
                None,
            )

        # -----------------------------------------
        # OTP expired
        # -----------------------------------------

        if timezone.now() > otp_record.expires_at:

            otp_record.verified = True

            otp_record.save(
                update_fields=[
                    "verified",
                ]
            )

            return (
                False,
                "OTP has expired.",
                otp_record,
            )

        # -----------------------------------------
        # Maximum attempts exceeded
        # -----------------------------------------

        if otp_record.attempts >= otp_record.max_attempts:

            otp_record.verified = True

            otp_record.save(
                update_fields=[
                    "verified",
                ]
            )

            return (
                False,
                "Too many verification attempts.",
                otp_record,
            )

        # -----------------------------------------
        # Register attempt
        # -----------------------------------------

        otp_record.attempts += 1

        # -----------------------------------------
        # Verify OTP
        # -----------------------------------------

        if not check_password(
            otp,
            otp_record.otp_hash,
        ):

            otp_record.save(
                update_fields=[
                    "attempts",
                ]
            )

            return (
                False,
                "Invalid OTP.",
                otp_record,
            )

        # -----------------------------------------
        # Successful verification
        # -----------------------------------------

        otp_record.verified = True

        otp_record.save(
            update_fields=[
                "attempts",
                "verified",
            ]
        )

        return (
            True,
            None,
            otp_record,
        )