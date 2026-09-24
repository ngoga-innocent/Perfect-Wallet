from rest_framework.routers import DefaultRouter

from .views import FinancialReminderViewSet,RegisterDeviceView
from django.urls import path

router = DefaultRouter()

router.register(
    r"",
    FinancialReminderViewSet,
    basename="financial-reminder",
)

urlpatterns = router.urls
urlpatterns += [
    path(
        "devices/register/",
        RegisterDeviceView.as_view(),
        name="register-device",
    ),
]