from rest_framework.routers import DefaultRouter

from .views import LoanViewSet


router = DefaultRouter()

router.register(
    r"",
    LoanViewSet,
    basename="loan",
)

urlpatterns = router.urls