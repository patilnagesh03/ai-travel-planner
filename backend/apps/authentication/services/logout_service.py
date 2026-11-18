from rest_framework_simplejwt.tokens import RefreshToken


class LogoutService:

    @staticmethod
    def logout(refresh_token):
        token = RefreshToken(refresh_token)
        token.blacklist()