from rest_framework.routers import DefaultRouter

from .views import TaskTemplateViewSet

router = DefaultRouter()
router.register("templates", TaskTemplateViewSet, basename="template")

urlpatterns = router.urls
