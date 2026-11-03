from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    NotificationViewSet,
    DevicePushTokenRegisterView,
    DevicePushTokenDeactivateView,
)

router = DefaultRouter()

router.register(
    "",
    NotificationViewSet,
    basename="notification",
)

urlpatterns = [
    path(
        "devices/register/",
        DevicePushTokenRegisterView.as_view(),
        name="register-device-token",
    ),
    path(
        "devices/deactivate/",
        DevicePushTokenDeactivateView.as_view(),
        name="deactivate-device-token",
    ),
] + router.urls