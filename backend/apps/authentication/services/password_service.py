from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError


User = get_user_model()


class PasswordService:

    @staticmethod
    def change_password(
        user: User, # type: ignore
        current_password: str,
        new_password: str,
    ) -> None:

        if not user.check_password(current_password):
            raise ValidationError(
                {
                    "current_password": "Current password is incorrect."
                }
            )

        user.set_password(new_password)
        user.save(update_fields=["password"])