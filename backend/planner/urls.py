from django.urls import path

from .views import PlanDayApplyView, PlanDayView

urlpatterns = [
    path("planner/plan-day/", PlanDayView.as_view(), name="plan-day"),
    path("planner/plan-day/apply/", PlanDayApplyView.as_view(), name="plan-day-apply"),
]
