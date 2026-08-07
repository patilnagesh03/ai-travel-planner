from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.apps.authentication.serializers.register_serializer import RegisterSerializer
from backend.apps.authentication.services.auth_service import AuthService


class RegisterView(APIView):

    permission_classes = []

    def post(self, request):

        serializer = RegisterSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        user = AuthService.register(serializer.validated_data)

        return Response(
            {
                "success": True,
                "message": "User registered successfully.",
                "data": {
                    "id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                },
            },
            status=status.HTTP_201_CREATED,
        )