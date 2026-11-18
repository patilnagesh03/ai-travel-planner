from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

from backend.apps.accounts.models import User


INVALID_REFRESH_TOKEN_MESSAGE = "Invalid or expired refresh token."


class RefreshTokenSerializer(TokenRefreshSerializer):
    """Translate unusable refresh tokens into a 401 response.

    SimpleJWT raises ``TokenError`` for malformed, expired or blacklisted
    tokens, and ``User.DoesNotExist`` when a token is still cryptographically
    valid but its account has been deleted. Neither is a DRF API exception,
    so without this translation the view would report them as unexpected
    server errors (500) instead of authentication failures (401).
    """

    def validate(self, attrs):
        try:
            return super().validate(attrs)
        except (TokenError, User.DoesNotExist) as exc:
            raise AuthenticationFailed(
                INVALID_REFRESH_TOKEN_MESSAGE
            ) from exc
