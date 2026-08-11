from backend.apps.accounts.models import User


class ProfileService:

    @staticmethod
    def get_profile(user: User) -> User:
        return user

    @staticmethod
    def update_profile(user: User, validated_data) -> User:
        for field, value in validated_data.items():
            setattr(user, field, value)

        user.save()

        return user