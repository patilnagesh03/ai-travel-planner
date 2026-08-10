from backend.apps.accounts.models import User


class ProfileService:

    @staticmethod
    def get_profile(user: User) -> User:
        return user