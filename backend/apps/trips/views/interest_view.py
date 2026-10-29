from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.apps.trips.models import Interest
from backend.apps.trips.serializers.interest_serializer import (
    InterestSerializer,
)


class InterestListView(APIView):
    """List the interests that can be attached to trip preferences."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        interests = Interest.objects.all()

        serializer = InterestSerializer(
            interests,
            many=True,
        )

        return Response(
            {
                "success": True,
                "message": "Interests retrieved successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
