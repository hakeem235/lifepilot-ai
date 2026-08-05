from django.urls import path

from .views import (
    CaptureApplyView,
    CaptureView,
    DailyReviewApplyView,
    DailyReviewView,
    PlanDayApplyView,
    PlanDayView,
)

urlpatterns = [
    path("planner/plan-day/", PlanDayView.as_view(), name="plan-day"),
    path("planner/plan-day/apply/", PlanDayApplyView.as_view(), name="plan-day-apply"),
    path("planner/capture/", CaptureView.as_view(), name="capture"),
    path("planner/capture/apply/", CaptureApplyView.as_view(), name="capture-apply"),
    path("planner/review/", DailyReviewView.as_view(), name="daily-review"),
    path("planner/review/apply/", DailyReviewApplyView.as_view(), name="daily-review-apply"),
]
