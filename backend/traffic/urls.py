from django.urls import path

from .views import CommuteOriginView, NextCommuteView

urlpatterns = [
    path("traffic/next-commute/", NextCommuteView.as_view(), name="next-commute"),
    path("traffic/origin/", CommuteOriginView.as_view(), name="commute-origin"),
]
