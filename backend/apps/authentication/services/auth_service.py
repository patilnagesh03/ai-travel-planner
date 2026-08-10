from backend.apps.accounts.models import User
from backend.apps.authentication.services.jwt_service import JWTService

class AuthService:

    @staticmethod
    def register(validated_data):

        validated_data.pop("confirm_password")

        password = validated_data.pop("password")

        user = User.objects.create_user(
            password=password,
            **validated_data,
        )

        return user

    @staticmethod
    def login(user):
        tokens = JWTService.generate_tokens(user)

        return {
            "user": user,
            "tokens": tokens,
        }