from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import NotificationViewSet, RegisterDeviceView

router = DefaultRouter()
router.register("notifications", NotificationViewSet, basename="notification")

urlpatterns = [
    path("notifications/register/", RegisterDeviceView.as_view()),
    *router.urls,
]
