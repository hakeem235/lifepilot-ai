from django.urls import path

from .views import BriefView, ChatView

urlpatterns = [
    path("ai/brief/", BriefView.as_view(), name="ai-brief"),
    path("ai/chat/", ChatView.as_view(), name="ai-chat"),
]
