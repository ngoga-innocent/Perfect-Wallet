import pyotp
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from common.email import EmailService
from common.otp import OTPService
from common.reset_tokens import create_password_reset_token, verify_password_reset_token
from common.responses import ApiResponse

from .models import UserSecurity
from .serializers import (
    CurrentUserSerializer,
    ForgotPasswordSerializer,
    LoginSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    SetupPinSerializer,
    UserSerializer,
    VerifyAuthenticatorSerializer,
    VerifyPasswordResetOTPSerializer,
    VerifyPinSerializer,
    ChangePasswordSerializer
)
from .utils import generate_qr_code, generate_totp_secret

User = get_user_model()
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from .serializers import (
    WalletFlowTokenRefreshSerializer,
    WalletFlowTokenVerifySerializer,
)

from django.shortcuts import render


def home(request):
    return render(request, "index.html")
class WalletFlowTokenVerifyView(TokenVerifyView):
    serializer_class = WalletFlowTokenVerifySerializer


class WalletFlowTokenRefreshView(TokenRefreshView):
    serializer_class = WalletFlowTokenRefreshSerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):

        try:
            serializer = RegisterSerializer(data=request.data)

            serializer.is_valid(raise_exception=True)

            user = serializer.save()

            return ApiResponse.success(
                message="Account created successfully.",
                data={"user": UserSerializer(user).data},
                status=status.HTTP_201_CREATED,
            )

        except ValidationError as e:
            return ApiResponse.error(
                message="Validation failed.",
                errors=e.detail,
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            print("SERVER ERROR:", e)

            return ApiResponse.error(
                message="Something went wrong.",
                data={"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )



    
class UserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get the currently authenticated user's profile.
        """
        serializer = UserSerializer(request.user)

        return ApiResponse.success(
            message="Profile retrieved successfully.",
            data=serializer.data,
        )

    def patch(self, request):
        """
        Update the currently authenticated user's profile.
        """
        serializer = UserSerializer(
            request.user,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return ApiResponse.success(
            message="Profile updated successfully.",
            data=UserSerializer(user).data,
        )

    def put(self, request):
        """
        Fully update the currently authenticated user's profile.
        """
        serializer = UserSerializer(
            request.user,
            data=request.data,
        )

        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return ApiResponse.success(
            message="Profile updated successfully.",
            data=UserSerializer(user).data,
        )

    def delete(self, request):
        """
        Permanently delete the authenticated user's account.
        """
        user = request.user

        try:
            user.delete()

            return ApiResponse.success(
                message="Account deleted successfully."
            )

        except Exception as e:
            print("DELETE ACCOUNT ERROR:", str(e))

            return ApiResponse.error(
                message="Unable to delete your account.",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):

        serializer = LoginSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        user = data["user"]

        # ---------------------------------------
        # Security configuration
        # ---------------------------------------

        try:
            security = user.security
        except UserSecurity.DoesNotExist:
            security = None

        methods = []

        if security:
            if security.pin_hash:
                methods.append("pin")

            if security.authenticator_enabled:
                methods.append("authenticator")

        security_setup_required = len(methods) == 0

        security_data = {
            "setup_required": security_setup_required,
            "verification_required": not security_setup_required,
            "methods": methods,
        }

        return ApiResponse.success(
            message="Login successful.",
            data={
                "access": data["access"],
                "refresh": data["refresh"],
                "user": UserSerializer(user).data,
                "security": security_data,
            },
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        print("===================Logging Out")
        try:
            refresh_token = request.data["refresh"]
            print()
            token = RefreshToken(refresh_token)

            token.blacklist()

            return ApiResponse.success(message="Logged out successfully")

        except Exception as e:
            print("Error",e)
            return (ApiResponse.error(message="Invalid token"),)


class SetupPinView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        # -----------------------------------------
        # Validate request data
        # -----------------------------------------

        serializer = SetupPinSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        pin = serializer.validated_data["pin"]

        try:
            # -----------------------------------------
            # Get or create security profile
            # -----------------------------------------

            security, created = UserSecurity.objects.get_or_create(user=request.user)

            # -----------------------------------------
            # Prevent unnecessary replacement
            # -----------------------------------------

            if security.pin_hash:
                return ApiResponse.error(
                    message="PIN is already configured.", status=400
                )

            # -----------------------------------------
            # Hash and save PIN
            # -----------------------------------------

            security.pin_hash = make_password(pin)

            security.save(update_fields=["pin_hash", "updated_at"])

            return ApiResponse.success(message="PIN setup completed successfully.")

        except Exception as e:
            print("SETUP PIN ERROR:", str(e))

            return ApiResponse.error(
                message="Unable to complete PIN setup.",
                data={"error": str(e)},
                status=500,
            )


class VerifyPinView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        try:
            serializer = VerifyPinSerializer(data=request.data)

            serializer.is_valid(raise_exception=True)

            security = request.user.security

            if not security.pin_hash:
                return ApiResponse.error(message="PIN is not enabled.", status=400)

            valid = check_password(serializer.validated_data["pin"], security.pin_hash)

            if not valid:
                return ApiResponse.error(message="Invalid PIN.", status=400)

            return ApiResponse.success(message="PIN verified.")
        except UserSecurity.DoesNotExist:
            return ApiResponse.error(message="Security profile not found.", status=404)
        except Exception as e:
            print("VERIFY PIN ERROR:", str(e))

            return ApiResponse.error(
                message="Unable to verify PIN.", data={"error": str(e)}, status=500
            )


class SetupAuthenticatorView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        security = request.user.security

        secret = generate_totp_secret()

        security.totp_secret = secret

        security.save()

        qr = generate_qr_code(secret, request.user.email)

        return ApiResponse.success(
            message="Authenticator setup initiated.",
            data={"secret": secret, "qr_code": qr["qr_code"]},
        )


class VerifyAuthenticatorView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        serializer = VerifyAuthenticatorSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        security = request.user.security

        if not security.totp_secret:
            return ApiResponse.error(message="Authenticator setup not started.")

        totp = pyotp.TOTP(security.totp_secret)

        valid = totp.verify(serializer.validated_data["code"])

        if not valid:
            return ApiResponse.error(message="Invalid authenticator code.")

        security.authenticator_enabled = True

        security.save()

        return ApiResponse.success(message="Authenticator enabled successfully.")


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):

        # -----------------------------------------
        # Validate request
        # -----------------------------------------

        serializer = ForgotPasswordSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        try:
            # -----------------------------------------
            # Find user
            # -----------------------------------------

            user = User.objects.filter(email__iexact=email).first()

            # -----------------------------------------
            # Do not reveal account existence
            # -----------------------------------------

            if not user:
                return ApiResponse.success(
                    message=(
                        "If an account exists for this email, "
                        "a verification code has been sent."
                    )
                )

            # -----------------------------------------
            # Generate OTP
            # -----------------------------------------

            otp_record, otp = OTPService.create(
                user=user,
                purpose="password_reset",
            )

            # -----------------------------------------
            # Send OTP email
            # -----------------------------------------

            try:
                EmailService.send_otp(
                    user=user,
                    otp=otp,
                    purpose="password_reset",
                )

            except Exception as email_error:
                # Invalidate OTP because the email
                # was not successfully sent.

                otp_record.verified = True

                otp_record.save(update_fields=["verified"])

                print("PASSWORD RESET EMAIL ERROR:", str(email_error))

                return ApiResponse.error(
                    message=(
                        "We could not send the "
                        "verification email. "
                        "Please try again later."
                    ),
                    status=503,
                )

            # -----------------------------------------
            # Success
            # -----------------------------------------

            return ApiResponse.success(
                message=(
                    "If an account exists for this email, "
                    "a verification code has been sent."
                )
            )

        # -----------------------------------------
        # Unexpected server errors
        # -----------------------------------------

        except Exception as e:
            print("FORGOT PASSWORD ERROR:", str(e))

            return ApiResponse.error(
                message=("Something went wrong while processing your request."),
                status=500,
            )


class VerifyPasswordResetOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):

        serializer = VerifyPasswordResetOTPSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        otp = serializer.validated_data["otp"]

        try:
            # -----------------------------------------
            # Find user
            # -----------------------------------------

            user = User.objects.filter(email__iexact=email).first()
            print(user)
            if not user:
                return ApiResponse.error(message="Invalid OTP.", status=400)

            # -----------------------------------------
            # Verify OTP
            # -----------------------------------------
            # print("Verifying OTP for user:", user.email,otp)
            verified, error = OTPService.verify(
                user=user,
                purpose="password_reset",
                otp=otp,
            )
            print(verified)

            if not verified:
                return ApiResponse.error(message=error or "Invalid OTP.", status=400)

            # -----------------------------------------
            # Get verified OTP record
            # -----------------------------------------

            otp_record = (
                user.otp_verifications.filter(
                    purpose="password_reset",
                    verified=True,
                )
                .order_by("-updated_at")
                .first()
            )

            if not otp_record:
                return ApiResponse.error(
                    message=("OTP verification could not be completed."), status=400
                )

            # -----------------------------------------
            # Generate reset token
            # -----------------------------------------

            reset_token = create_password_reset_token(
                user=user, otp_id=otp_record.id, purpose="password_reset"
            )

            return ApiResponse.success(
                message="OTP verified successfully.",
                data={
                    "reset_token": reset_token,
                    "expires_in": 600,
                },
            )

        except Exception as e:
            print("PASSWORD OTP VERIFICATION ERROR:", str(e))

            return ApiResponse.error(
                message=("Something went wrong while verifying the OTP."), status=500
            )


from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import (
    validate_password,
)
from django.core import signing
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from .serializers import (
    ResetPasswordSerializer,
)

User = get_user_model()


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):

        serializer = ResetPasswordSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        reset_token = serializer.validated_data["reset_token"]

        new_password = serializer.validated_data["new_password"]

        try:
            # -----------------------------------------
            # Validate reset token
            # -----------------------------------------

            try:
                payload = verify_password_reset_token(reset_token)

            except signing.SignatureExpired:
                return ApiResponse.error(
                    message=("Password reset session has expired."), status=400
                )

            except signing.BadSignature:
                return ApiResponse.error(
                    message=("Invalid password reset token."), status=400
                )

            # -----------------------------------------
            # Validate purpose
            # -----------------------------------------

            if payload.get("purpose") != "password_reset":
                return ApiResponse.error(
                    message=("Invalid password reset token."), status=400
                )

            # -----------------------------------------
            # Get user
            # -----------------------------------------

            user = User.objects.filter(id=payload.get("user_id")).first()

            if not user:
                return ApiResponse.error(
                    message=("Invalid password reset request."), status=400
                )

            # -----------------------------------------
            # Validate password
            # -----------------------------------------

            try:
                validate_password(
                    new_password,
                    user=user,
                )

            except Exception as password_error:
                return ApiResponse.error(
                    message="Password is not valid.",
                    data={"errors": password_error.messages},
                    status=400,
                )

            # -----------------------------------------
            # Set password
            # -----------------------------------------

            user.set_password(new_password)

            user.save(update_fields=["password"])

            # -----------------------------------------
            # Security notification
            # -----------------------------------------

            try:
                EmailService.send_password_changed(user=user)

            except Exception as email_error:
                print("PASSWORD CHANGE EMAIL ERROR:", str(email_error))

                # Password was already changed.
                # Do not fail the reset operation.

            # -----------------------------------------
            # Success
            # -----------------------------------------

            return ApiResponse.success(message=("Password reset successfully."))

        except Exception as e:
            print("PASSWORD RESET ERROR:", str(e))

            return ApiResponse.error(
                message=("Something went wrong while resetting your password."),
                status=500,
            )


class ForgotPinView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        try:
            user = request.user

            # -----------------------------------------
            # Create OTP
            # -----------------------------------------

            otp_record, otp = OTPService.create(
                user=user,
                purpose="pin_reset",
            )

            # -----------------------------------------
            # Send OTP
            # -----------------------------------------

            try:
                EmailService.send_otp(
                    user=user,
                    otp=otp,
                    purpose="pin_reset",
                )

            except Exception as email_error:
                print("PIN RESET EMAIL ERROR:", str(email_error))

                # Invalidate OTP

                otp_record.verified = True

                otp_record.save(update_fields=["verified"])

                return ApiResponse.error(
                    message=(
                        "We could not send the "
                        "verification code. "
                        "Please try again later."
                    ),
                    status=503,
                )

            return ApiResponse.success(
                message=("A verification code has been sent to your registered email.")
            )

        except Exception as e:
            print("FORGOT PIN ERROR:", str(e))

            return ApiResponse.error(
                message=("Something went wrong while processing your request."),
                status=500,
            )


class VerifyPinResetOTPView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        print("===================================")
        print("CONTENT TYPE:", request.content_type)
        print("RAW BODY:", request.body)
        print("REQUEST DATA:", request.data)
        print("USER:", request.user)
        print("===================================")
        otp = request.data.get("otp")
        print(request.data)
        if not otp:
            return ApiResponse.error(message="OTP is required.", status=400)

        if len(otp) != 6 or not otp.isdigit():
            return ApiResponse.error(message="OTP must be a 6-digit code.", status=400)

        try:
            user = request.user

            # -----------------------------------------
            # Verify OTP against authenticated user
            # -----------------------------------------

            verified, error, otp_record = OTPService.verify_with_record(
                user=user,
                purpose="pin_reset",
                otp=otp,
            )

            if not verified:
                return ApiResponse.error(message=(error or "Invalid OTP."), status=400)

            # -----------------------------------------
            # Create PIN reset authorization
            # -----------------------------------------

            reset_token = create_password_reset_token(
                user=user,
                otp_id=otp_record.id,
                purpose="pin_reset",
            )

            return ApiResponse.success(
                message=("OTP verified successfully."),
                data={
                    "reset_token": reset_token,
                    "expires_in": 600,
                },
            )

        except Exception as e:
            print("PIN OTP VERIFICATION ERROR:", str(e))

            return ApiResponse.error(
                message=("Something went wrong while verifying the OTP."), status=500
            )


class ResetPinView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        reset_token = request.data.get("reset_token")

        pin = request.data.get("pin")

        confirm_pin = request.data.get("confirm_pin")

        # -----------------------------------------
        # Validate request
        # -----------------------------------------

        if not reset_token:
            return ApiResponse.error(message="Reset token is required.", status=400)

        if not pin:
            return ApiResponse.error(message="PIN is required.", status=400)

        if not confirm_pin:
            return ApiResponse.error(
                message="PIN confirmation is required.", status=400
            )

        if not pin.isdigit():
            return ApiResponse.error(
                message="PIN must contain only numbers.", status=400
            )

        if len(pin) != 6:
            return ApiResponse.error(
                message="PIN must contain exactly 6 digits.", status=400
            )

        if pin != confirm_pin:
            return ApiResponse.error(message="PINs do not match.", status=400)

        try:
            # -----------------------------------------
            # Verify reset token
            # -----------------------------------------

            try:
                payload = verify_password_reset_token(reset_token)

            except signing.SignatureExpired:
                return ApiResponse.error(
                    message=("PIN reset session has expired."), status=400
                )

            except signing.BadSignature:
                return ApiResponse.error(
                    message=("Invalid PIN reset token."), status=400
                )

            # -----------------------------------------
            # Verify purpose
            # -----------------------------------------

            if payload.get("purpose") != "pin_reset":
                return ApiResponse.error(
                    message=("Invalid PIN reset token."), status=400
                )

            # -----------------------------------------
            # Ensure token belongs to current user
            # -----------------------------------------

            if str(payload.get("user_id")) != str(request.user.id):
                return ApiResponse.error(
                    message=("Invalid PIN reset request."), status=403
                )

            # -----------------------------------------
            # Get/create security record
            # -----------------------------------------

            security, created = UserSecurity.objects.get_or_create(user=request.user)

            # -----------------------------------------
            # Save hashed PIN
            # -----------------------------------------

            security.pin_hash = make_password(pin)

            security.pin_enabled = True

            security.save(
                update_fields=[
                    "pin_hash",
                    "pin_enabled",
                    "updated_at",
                ]
            )

            return ApiResponse.success(message=("Wallet PIN reset successfully."))

        except Exception as e:
            print("PIN RESET ERROR:", str(e))

            return ApiResponse.error(
                message=("Something went wrong while resetting your PIN."), status=500
            )
import pyotp
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from common.email import EmailService
from common.otp import OTPService
from common.reset_tokens import create_password_reset_token, verify_password_reset_token
from common.responses import ApiResponse

from .models import UserSecurity
from .serializers import (
    CurrentUserSerializer,
    ForgotPasswordSerializer,
    LoginSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    SetupPinSerializer,
    UserSerializer,
    VerifyAuthenticatorSerializer,
    VerifyPasswordResetOTPSerializer,
    VerifyPinSerializer,
)
from .utils import generate_qr_code, generate_totp_secret

User = get_user_model()
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from .serializers import (
    WalletFlowTokenRefreshSerializer,
    WalletFlowTokenVerifySerializer,
)


class WalletFlowTokenVerifyView(TokenVerifyView):
    serializer_class = WalletFlowTokenVerifySerializer


class WalletFlowTokenRefreshView(TokenRefreshView):
    serializer_class = WalletFlowTokenRefreshSerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):

        try:
            serializer = RegisterSerializer(data=request.data)

            serializer.is_valid(raise_exception=True)

            user = serializer.save()

            return ApiResponse.success(
                message="Account created successfully.",
                data={"user": UserSerializer(user).data},
                status=status.HTTP_201_CREATED,
            )

        except ValidationError as e:
            return ApiResponse.error(
                message="Validation failed.",
                errors=e.detail,
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            print("SERVER ERROR:", e)

            return ApiResponse.error(
                message="Something went wrong.",
                data={"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )



    
class UserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get the currently authenticated user's profile.
        """
        serializer = UserSerializer(request.user)

        return ApiResponse.success(
            message="Profile retrieved successfully.",
            data=serializer.data,
        )

    def patch(self, request):
        """
        Update the currently authenticated user's profile.
        """
        serializer = UserSerializer(
            request.user,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return ApiResponse.success(
            message="Profile updated successfully.",
            data=UserSerializer(user).data,
        )

    def put(self, request):
        """
        Fully update the currently authenticated user's profile.
        """
        serializer = UserSerializer(
            request.user,
            data=request.data,
        )

        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return ApiResponse.success(
            message="Profile updated successfully.",
            data=UserSerializer(user).data,
        )

    def delete(self, request):
        """
        Permanently delete the authenticated user's account.
        """
        user = request.user

        try:
            user.delete()

            return ApiResponse.success(
                message="Account deleted successfully."
            )

        except Exception as e:
            print("DELETE ACCOUNT ERROR:", str(e))

            return ApiResponse.error(
                message="Unable to delete your account.",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):

        serializer = LoginSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        user = data["user"]

        # ---------------------------------------
        # Security configuration
        # ---------------------------------------

        try:
            security = user.security
        except UserSecurity.DoesNotExist:
            security = None

        methods = []

        if security:
            if security.pin_hash:
                methods.append("pin")

            if security.authenticator_enabled:
                methods.append("authenticator")

        security_setup_required = len(methods) == 0

        security_data = {
            "setup_required": security_setup_required,
            "verification_required": not security_setup_required,
            "methods": methods,
        }

        return ApiResponse.success(
            message="Login successful.",
            data={
                "access": data["access"],
                "refresh": data["refresh"],
                "user": UserSerializer(user).data,
                "security": security_data,
            },
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        print("===================Logging Out")
        try:
            refresh_token = request.data["refresh"]
            print()
            token = RefreshToken(refresh_token)

            token.blacklist()

            return ApiResponse.success(message="Logged out successfully")

        except Exception as e:
            print("Error",e)
            return (ApiResponse.error(message="Invalid token"),)


class SetupPinView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        # -----------------------------------------
        # Validate request data
        # -----------------------------------------

        serializer = SetupPinSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        pin = serializer.validated_data["pin"]

        try:
            # -----------------------------------------
            # Get or create security profile
            # -----------------------------------------

            security, created = UserSecurity.objects.get_or_create(user=request.user)

            # -----------------------------------------
            # Prevent unnecessary replacement
            # -----------------------------------------

            if security.pin_hash:
                return ApiResponse.error(
                    message="PIN is already configured.", status=400
                )

            # -----------------------------------------
            # Hash and save PIN
            # -----------------------------------------

            security.pin_hash = make_password(pin)

            security.save(update_fields=["pin_hash", "updated_at"])

            return ApiResponse.success(message="PIN setup completed successfully.")

        except Exception as e:
            print("SETUP PIN ERROR:", str(e))

            return ApiResponse.error(
                message="Unable to complete PIN setup.",
                data={"error": str(e)},
                status=500,
            )


class VerifyPinView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        try:
            serializer = VerifyPinSerializer(data=request.data)

            serializer.is_valid(raise_exception=True)

            security = request.user.security

            if not security.pin_hash:
                return ApiResponse.error(message="PIN is not enabled.", status=400)

            valid = check_password(serializer.validated_data["pin"], security.pin_hash)

            if not valid:
                return ApiResponse.error(message="Invalid PIN.", status=400)

            return ApiResponse.success(message="PIN verified.")
        except UserSecurity.DoesNotExist:
            return ApiResponse.error(message="Security profile not found.", status=404)
        except Exception as e:
            print("VERIFY PIN ERROR:", str(e))

            return ApiResponse.error(
                message="Unable to verify PIN.", data={"error": str(e)}, status=500
            )


class SetupAuthenticatorView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        security = request.user.security

        secret = generate_totp_secret()

        security.totp_secret = secret

        security.save()

        qr = generate_qr_code(secret, request.user.email)

        return ApiResponse.success(
            message="Authenticator setup initiated.",
            data={"secret": secret, "qr_code": qr["qr_code"]},
        )


class VerifyAuthenticatorView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        serializer = VerifyAuthenticatorSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        security = request.user.security

        if not security.totp_secret:
            return ApiResponse.error(message="Authenticator setup not started.")

        totp = pyotp.TOTP(security.totp_secret)

        valid = totp.verify(serializer.validated_data["code"])

        if not valid:
            return ApiResponse.error(message="Invalid authenticator code.")

        security.authenticator_enabled = True

        security.save()

        return ApiResponse.success(message="Authenticator enabled successfully.")


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):

        # -----------------------------------------
        # Validate request
        # -----------------------------------------

        serializer = ForgotPasswordSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        try:
            # -----------------------------------------
            # Find user
            # -----------------------------------------

            user = User.objects.filter(email__iexact=email).first()

            # -----------------------------------------
            # Do not reveal account existence
            # -----------------------------------------

            if not user:
                return ApiResponse.success(
                    message=(
                        "If an account exists for this email, "
                        "a verification code has been sent."
                    )
                )

            # -----------------------------------------
            # Generate OTP
            # -----------------------------------------

            otp_record, otp = OTPService.create(
                user=user,
                purpose="password_reset",
            )

            # -----------------------------------------
            # Send OTP email
            # -----------------------------------------

            try:
                EmailService.send_otp(
                    user=user,
                    otp=otp,
                    purpose="password_reset",
                )

            except Exception as email_error:
                # Invalidate OTP because the email
                # was not successfully sent.

                otp_record.verified = True

                otp_record.save(update_fields=["verified"])

                print("PASSWORD RESET EMAIL ERROR:", str(email_error))

                return ApiResponse.error(
                    message=(
                        "We could not send the "
                        "verification email. "
                        "Please try again later."
                    ),
                    status=503,
                )

            # -----------------------------------------
            # Success
            # -----------------------------------------

            return ApiResponse.success(
                message=(
                    "If an account exists for this email, "
                    "a verification code has been sent."
                )
            )

        # -----------------------------------------
        # Unexpected server errors
        # -----------------------------------------

        except Exception as e:
            print("FORGOT PASSWORD ERROR:", str(e))

            return ApiResponse.error(
                message=("Something went wrong while processing your request."),
                status=500,
            )


class VerifyPasswordResetOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):

        serializer = VerifyPasswordResetOTPSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        otp = serializer.validated_data["otp"]

        try:
            # -----------------------------------------
            # Find user
            # -----------------------------------------

            user = User.objects.filter(email__iexact=email).first()
            print(user)
            if not user:
                return ApiResponse.error(message="Invalid OTP.", status=400)

            # -----------------------------------------
            # Verify OTP
            # -----------------------------------------
            # print("Verifying OTP for user:", user.email,otp)
            verified, error = OTPService.verify(
                user=user,
                purpose="password_reset",
                otp=otp,
            )
            print(verified)

            if not verified:
                return ApiResponse.error(message=error or "Invalid OTP.", status=400)

            # -----------------------------------------
            # Get verified OTP record
            # -----------------------------------------

            otp_record = (
                user.otp_verifications.filter(
                    purpose="password_reset",
                    verified=True,
                )
                .order_by("-updated_at")
                .first()
            )

            if not otp_record:
                return ApiResponse.error(
                    message=("OTP verification could not be completed."), status=400
                )

            # -----------------------------------------
            # Generate reset token
            # -----------------------------------------

            reset_token = create_password_reset_token(
                user=user, otp_id=otp_record.id, purpose="password_reset"
            )

            return ApiResponse.success(
                message="OTP verified successfully.",
                data={
                    "reset_token": reset_token,
                    "expires_in": 600,
                },
            )

        except Exception as e:
            print("PASSWORD OTP VERIFICATION ERROR:", str(e))

            return ApiResponse.error(
                message=("Something went wrong while verifying the OTP."), status=500
            )


from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import (
    validate_password,
)
from django.core import signing
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from .serializers import (
    ResetPasswordSerializer,
)

User = get_user_model()


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):

        serializer = ResetPasswordSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        reset_token = serializer.validated_data["reset_token"]

        new_password = serializer.validated_data["new_password"]

        try:
            # -----------------------------------------
            # Validate reset token
            # -----------------------------------------

            try:
                payload = verify_password_reset_token(reset_token)

            except signing.SignatureExpired:
                return ApiResponse.error(
                    message=("Password reset session has expired."), status=400
                )

            except signing.BadSignature:
                return ApiResponse.error(
                    message=("Invalid password reset token."), status=400
                )

            # -----------------------------------------
            # Validate purpose
            # -----------------------------------------

            if payload.get("purpose") != "password_reset":
                return ApiResponse.error(
                    message=("Invalid password reset token."), status=400
                )

            # -----------------------------------------
            # Get user
            # -----------------------------------------

            user = User.objects.filter(id=payload.get("user_id")).first()

            if not user:
                return ApiResponse.error(
                    message=("Invalid password reset request."), status=400
                )

            # -----------------------------------------
            # Validate password
            # -----------------------------------------

            try:
                validate_password(
                    new_password,
                    user=user,
                )

            except Exception as password_error:
                return ApiResponse.error(
                    message="Password is not valid.",
                    data={"errors": password_error.messages},
                    status=400,
                )

            # -----------------------------------------
            # Set password
            # -----------------------------------------

            user.set_password(new_password)

            user.save(update_fields=["password"])

            # -----------------------------------------
            # Security notification
            # -----------------------------------------

            try:
                EmailService.send_password_changed(user=user)

            except Exception as email_error:
                print("PASSWORD CHANGE EMAIL ERROR:", str(email_error))

                # Password was already changed.
                # Do not fail the reset operation.

            # -----------------------------------------
            # Success
            # -----------------------------------------

            return ApiResponse.success(message=("Password reset successfully."))

        except Exception as e:
            print("PASSWORD RESET ERROR:", str(e))

            return ApiResponse.error(
                message=("Something went wrong while resetting your password."),
                status=500,
            )


class ForgotPinView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        try:
            user = request.user

            # -----------------------------------------
            # Create OTP
            # -----------------------------------------

            otp_record, otp = OTPService.create(
                user=user,
                purpose="pin_reset",
            )

            # -----------------------------------------
            # Send OTP
            # -----------------------------------------

            try:
                EmailService.send_otp(
                    user=user,
                    otp=otp,
                    purpose="pin_reset",
                )

            except Exception as email_error:
                print("PIN RESET EMAIL ERROR:", str(email_error))

                # Invalidate OTP

                otp_record.verified = True

                otp_record.save(update_fields=["verified"])

                return ApiResponse.error(
                    message=(
                        "We could not send the "
                        "verification code. "
                        "Please try again later."
                    ),
                    status=503,
                )

            return ApiResponse.success(
                message=("A verification code has been sent to your registered email.")
            )

        except Exception as e:
            print("FORGOT PIN ERROR:", str(e))

            return ApiResponse.error(
                message=("Something went wrong while processing your request."),
                status=500,
            )


class VerifyPinResetOTPView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        print("===================================")
        print("CONTENT TYPE:", request.content_type)
        print("RAW BODY:", request.body)
        print("REQUEST DATA:", request.data)
        print("USER:", request.user)
        print("===================================")
        otp = request.data.get("otp")
        print(request.data)
        if not otp:
            return ApiResponse.error(message="OTP is required.", status=400)

        if len(otp) != 6 or not otp.isdigit():
            return ApiResponse.error(message="OTP must be a 6-digit code.", status=400)

        try:
            user = request.user

            # -----------------------------------------
            # Verify OTP against authenticated user
            # -----------------------------------------

            verified, error, otp_record = OTPService.verify_with_record(
                user=user,
                purpose="pin_reset",
                otp=otp,
            )

            if not verified:
                return ApiResponse.error(message=(error or "Invalid OTP."), status=400)

            # -----------------------------------------
            # Create PIN reset authorization
            # -----------------------------------------

            reset_token = create_password_reset_token(
                user=user,
                otp_id=otp_record.id,
                purpose="pin_reset",
            )

            return ApiResponse.success(
                message=("OTP verified successfully."),
                data={
                    "reset_token": reset_token,
                    "expires_in": 600,
                },
            )

        except Exception as e:
            print("PIN OTP VERIFICATION ERROR:", str(e))

            return ApiResponse.error(
                message=("Something went wrong while verifying the OTP."), status=500
            )


class ResetPinView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        reset_token = request.data.get("reset_token")

        pin = request.data.get("pin")

        confirm_pin = request.data.get("confirm_pin")

        # -----------------------------------------
        # Validate request
        # -----------------------------------------

        if not reset_token:
            return ApiResponse.error(message="Reset token is required.", status=400)

        if not pin:
            return ApiResponse.error(message="PIN is required.", status=400)

        if not confirm_pin:
            return ApiResponse.error(
                message="PIN confirmation is required.", status=400
            )

        if not pin.isdigit():
            return ApiResponse.error(
                message="PIN must contain only numbers.", status=400
            )

        if len(pin) != 6:
            return ApiResponse.error(
                message="PIN must contain exactly 6 digits.", status=400
            )

        if pin != confirm_pin:
            return ApiResponse.error(message="PINs do not match.", status=400)

        try:
            # -----------------------------------------
            # Verify reset token
            # -----------------------------------------

            try:
                payload = verify_password_reset_token(reset_token)

            except signing.SignatureExpired:
                return ApiResponse.error(
                    message=("PIN reset session has expired."), status=400
                )

            except signing.BadSignature:
                return ApiResponse.error(
                    message=("Invalid PIN reset token."), status=400
                )

            # -----------------------------------------
            # Verify purpose
            # -----------------------------------------

            if payload.get("purpose") != "pin_reset":
                return ApiResponse.error(
                    message=("Invalid PIN reset token."), status=400
                )

            # -----------------------------------------
            # Ensure token belongs to current user
            # -----------------------------------------

            if str(payload.get("user_id")) != str(request.user.id):
                return ApiResponse.error(
                    message=("Invalid PIN reset request."), status=403
                )

            # -----------------------------------------
            # Get/create security record
            # -----------------------------------------

            security, created = UserSecurity.objects.get_or_create(user=request.user)

            # -----------------------------------------
            # Save hashed PIN
            # -----------------------------------------

            security.pin_hash = make_password(pin)

            security.pin_enabled = True

            security.save(
                update_fields=[
                    "pin_hash",
                    "pin_enabled",
                    "updated_at",
                ]
            )

            return ApiResponse.success(message=("Wallet PIN reset successfully."))

        except Exception as e:
            print("PIN RESET ERROR:", str(e))

            return ApiResponse.error(
                message=("Something went wrong while resetting your PIN."), status=500
            )
 

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request},
        )

        serializer.is_valid(raise_exception=True)

        user = request.user

        try:
            # -----------------------------------------
            # Set new password
            # -----------------------------------------

            user.set_password(
                serializer.validated_data["new_password"]
            )

            user.save(update_fields=["password"])

            # -----------------------------------------
            # Security notification
            # -----------------------------------------

            try:
                EmailService.send_password_changed(user=user)

            except Exception as email_error:
                # Password was already changed.
                # Do not fail the operation because
                # notification email failed.

                print(
                    "PASSWORD CHANGE EMAIL ERROR:",
                    str(email_error),
                )

            return ApiResponse.success(
                message="Password changed successfully."
            )

        except Exception as e:
            print("CHANGE PASSWORD ERROR:", str(e))

            return ApiResponse.error(
                message="Something went wrong while changing your password.",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
# core/views.py

from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAdminUser

from .models import AppVersion
from .serializers import AppVersionSerializer


class AppVersionViewSet(viewsets.ModelViewSet):
    queryset = AppVersion.objects.all().order_by("-updated_at")
    serializer_class = AppVersionSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]

        return [IsAdminUser()]

    def get_queryset(self):
        queryset = AppVersion.objects.all()

        platform = self.request.query_params.get("platform")

        if platform:
            queryset = queryset.filter(
                platform=platform,
                is_active=True,
            )

        return queryset.order_by("-updated_at")