from django.urls import path

from .views import (
   
    ForgotPasswordView,
    ForgotPinView,
    LoginView,
    LogoutView,
    RegisterView,
    ResetPasswordView,
    ResetPinView,
    SetupAuthenticatorView,
    SetupPinView,
    VerifyAuthenticatorView,
    VerifyPasswordResetOTPView,
    VerifyPinResetOTPView,
    VerifyPinView,
    WalletFlowTokenRefreshView,
    WalletFlowTokenVerifyView,
    UserView,
    ChangePasswordView
)

from rest_framework.routers import DefaultRouter
from .views import AppVersionViewSet

router = DefaultRouter()

router.register(
    r"app-versions",
    AppVersionViewSet,
    basename="app-version",
)

urlpatterns = router.urls
urlpatterns += [
    path("register/", RegisterView.as_view()),
    path("login/", LoginView.as_view()),
    path("token/refresh/", WalletFlowTokenRefreshView.as_view()),
    path("logout/", LogoutView.as_view()),
    path("security/pin/setup/", SetupPinView.as_view()),
    path("security/pin/verify/", VerifyPinView.as_view()),
    path("security/authenticator/setup/", SetupAuthenticatorView.as_view()),
    path("security/authenticator/verify/", VerifyAuthenticatorView.as_view()),
    # RESETING PASSWORD AND ACCOUNT PIN
    path("password/forgot/", ForgotPasswordView.as_view()),
    path("password/verify-otp/", VerifyPasswordResetOTPView.as_view()),
    path("password/reset/", ResetPasswordView.as_view()),
    path("security/pin_reset/request_otp/", ForgotPinView.as_view()),
    path("security/pin_reset/verify_otp/", VerifyPinResetOTPView.as_view()),
    path("security/pin_reset/rest_pin/", ResetPinView.as_view()),
    path(
        "token/verify/",
        WalletFlowTokenVerifyView.as_view(),
        name="token-verify",
    ),
   
    path("me/", UserView.as_view(), name="user-detail"),
 
    path(
        "change-password/",
        ChangePasswordView.as_view(),
        name="change-password",
    ),
]
