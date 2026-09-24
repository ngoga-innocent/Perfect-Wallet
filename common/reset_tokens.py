from django.core import signing
from authentication.models import OTPVerification

PASSWORD_RESET_SALT = "walletflow-password-reset"


def create_password_reset_token(
    *,
    user,
    otp_id,
    purpose
):
    return signing.dumps(
        {
            "user_id": user.id,
            "otp_id": otp_id,
            "purpose": purpose,
        },
        salt=PASSWORD_RESET_SALT,
    )


def verify_password_reset_token(
    token,
):
    return signing.loads(
        token,
        salt=PASSWORD_RESET_SALT,
        max_age=600,  # 10 minutes
    )


@staticmethod
def get_latest_verified(
    *,
    user,
    purpose,
):
    return (
        OTPVerification.objects
        .filter(
            user=user,
            purpose=purpose,
            verified=True,
        )
        .order_by("-created_at")
        .first()
    )