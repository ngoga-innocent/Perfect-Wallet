from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    password_confirmation = serializers.CharField(write_only=True)

    class Meta:
        model = User

        fields = [
            "id",
            "email",
            "phone_number",
            "password",
            "first_name",
            "last_name",
            "password_confirmation",
        ]

    def validate(self, attrs):

        if attrs["password"] != attrs["password_confirmation"]:
            raise serializers.ValidationError({"password": "Passwords do not match"})

        return attrs

    def create(self, validated_data):

        validated_data.pop("password_confirmation")

        user = User.objects.create_user(
            email=validated_data["email"],
            phone_number=validated_data.get("phone_number"),
            password=validated_data["password"],
        )

        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()

    password = serializers.CharField(write_only=True)

    def validate(self, attrs):

        user = authenticate(email=attrs["email"], password=attrs["password"])

        if not user:
            raise serializers.ValidationError("Invalid credentials")

        if not user.is_active:
            raise serializers.ValidationError("Account disabled")

        refresh = RefreshToken.for_user(user)

        return {
            "user": user,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "is_active",
        ]
        read_only_fields = [
            "id",
            "email",
        ]


class SetupPinSerializer(serializers.Serializer):
    pin = serializers.CharField(min_length=4, max_length=6, write_only=True)

    confirm_pin = serializers.CharField(write_only=True)

    def validate(self, attrs):

        if attrs["pin"] != attrs["confirm_pin"]:
            raise serializers.ValidationError(
                {"pin": "PIN confirmation does not match."}
            )

        return attrs


class VerifyPinSerializer(serializers.Serializer):
    pin = serializers.CharField(write_only=True)


class VerifyAuthenticatorSerializer(serializers.Serializer):
    code = serializers.CharField(min_length=6, max_length=6)


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class VerifyPasswordResetOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

    otp = serializers.CharField(
        min_length=6,
        max_length=6,
    )


class ResetPasswordSerializer(serializers.Serializer):
    reset_token = serializers.CharField()

    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
    )

    confirm_password = serializers.CharField(
        write_only=True,
        min_length=8,
    )

    def validate(self, attrs):

        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )

        return attrs


# REFRESH TOKEN
# from rest_framework_simplejwt.serializers import TokenRefreshSerializer


class WalletFlowTokenRefreshSerializer(TokenRefreshSerializer):
    """
    Handles refresh token validation and returns
    a new access token.
    """

    def validate(self, attrs):
        data = super().validate(attrs)

        return {
            "access": data["access"],
            **({"refresh": data["refresh"]} if "refresh" in data else {}),
        }


from rest_framework_simplejwt.serializers import TokenVerifySerializer


class WalletFlowTokenVerifySerializer(TokenVerifySerializer):
    pass
    from rest_framework import serializers

    from .models import User


class CurrentUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        write_only=True,
        required=True,
        trim_whitespace=False,
    )

    new_password = serializers.CharField(
        write_only=True,
        required=True,
        trim_whitespace=False,
    )

    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        trim_whitespace=False,
    )

    def validate(self, attrs):
        user = self.context["request"].user

        current_password = attrs["current_password"]
        new_password = attrs["new_password"]
        confirm_password = attrs["confirm_password"]

        # -----------------------------------------
        # Verify current password
        # -----------------------------------------

        if not user.check_password(current_password):
            raise serializers.ValidationError(
                {
                    "current_password": "Current password is incorrect."
                }
            )

        # -----------------------------------------
        # Confirm new password
        # -----------------------------------------

        if new_password != confirm_password:
            raise serializers.ValidationError(
                {
                    "confirm_password": "New passwords do not match."
                }
            )

        # -----------------------------------------
        # Prevent reusing current password
        # -----------------------------------------

        if user.check_password(new_password):
            raise serializers.ValidationError(
                {
                    "new_password": (
                        "New password must be different from your current password."
                    )
                }
            )

        # -----------------------------------------
        # Django password validation
        # -----------------------------------------

        try:
            validate_password(
                new_password,
                user=user,
            )
        except serializers.ValidationError:
            raise
        except Exception as error:
            raise serializers.ValidationError(
                {
                    "new_password": error.messages
                }
            )

        return attrs
