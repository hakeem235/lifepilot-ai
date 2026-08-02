from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import build_insights


class InsightsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(build_insights(request.user))
