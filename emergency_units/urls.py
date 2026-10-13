
from rest_framework.routers import DefaultRouter

from .views import AdminEmergencyUnitViewSet

router = DefaultRouter()
router.register(
    "",
    AdminEmergencyUnitViewSet,
    basename="admin-emergency-unit",
)

urlpatterns = router.urls
