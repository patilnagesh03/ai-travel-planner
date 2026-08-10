from rest_framework import serializers

from backend.apps.accounts.models import User


class ProfileSerializer(serializers.ModelSerializer):

    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone_number",
            "profile_picture",
            "country",
            "city",
            "date_of_birth",
            "is_verified",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "email",
            "full_name",
            "is_verified",
            "created_at",
            "updated_at",
        )