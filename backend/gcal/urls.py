from django.urls import path

from .views import (
    CalendarAuthURLView,
    CalendarCallbackView,
    CalendarDisconnectView,
    CalendarEventsView,
    CalendarFinalizeView,
    CalendarStatusView,
)

urlpatterns = [
    path("gcal/status/", CalendarStatusView.as_view()),
    path("gcal/auth-url/", CalendarAuthURLView.as_view()),
    path("gcal/callback/", CalendarCallbackView.as_view()),
    path("gcal/finalize/", CalendarFinalizeView.as_view()),
    path("gcal/events/", CalendarEventsView.as_view()),
    path("gcal/disconnect/", CalendarDisconnectView.as_view()),
]
