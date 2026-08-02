"""Root URL configuration for the LifePilot AI backend."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
    path("api/", include("users.urls")),
    path("api/", include("tasks.urls")),
    path("api/", include("assistant.urls")),
    path("api/", include("insights.urls")),
]
