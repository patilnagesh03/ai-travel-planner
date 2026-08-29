from rest_framework import serializers
from backend.apps.itinerary.enums import ActivityType
from backend.apps.itinerary.models import ItineraryItem


class ItineraryItemSerializer(serializers.ModelSerializer):

    activity_type = serializers.ChoiceField(
        choices=ActivityType.choices,
        required=False,
        default=ActivityType.OTHER,
    )

    latitude = serializers.DecimalField(
        max_digits=10,
        decimal_places=7,
        required=False,
        allow_null=True,
    )

    longitude = serializers.DecimalField(
        max_digits=10,
        decimal_places=7,
        required=False,
        allow_null=True,
    )

    order = serializers.IntegerField(
        min_value=1,
        required=False,
        default=1,
    )

    class Meta:
        model = ItineraryItem

        fields = (
            "id",
            "itinerary",
            "date",
            "start_time",
            "end_time",
            "title",
            "description",
            "location_name",
            "location_address",
            "latitude",
            "longitude",
            "activity_type",
            "order",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "itinerary",
            "created_at",
            "updated_at",
        )

    def validate_title(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Title cannot be empty."
            )

        return value

    def validate_description(self, value):
        if value is None:
            return value

        return value.strip()

    def validate_location_name(self, value):
        if value is None:
            return value

        value = value.strip()

        return value

    def validate_location_address(self, value):
        if value is None:
            return value

        value = value.strip()

        return value

    def validate_latitude(self, value):
        if value is not None and not (-90 <= value <= 90):
            raise serializers.ValidationError(
                "Latitude must be between -90 and 90."
            )

        return value

    def validate_longitude(self, value):
        if value is not None and not (-180 <= value <= 180):
            raise serializers.ValidationError(
                "Longitude must be between -180 and 180."
            )

        return value

    def validate(self, attrs):

        date = attrs.get("date")

        start_time = attrs.get("start_time")
        end_time = attrs.get("end_time")

        # Handle PATCH correctly.
        if self.instance:
            date = attrs.get(
                "date",
                self.instance.date,
            )

            start_time = attrs.get(
                "start_time",
                self.instance.start_time,
            )

            end_time = attrs.get(
                "end_time",
                self.instance.end_time,
            )

        # Validate time range.
        if (
            start_time
            and end_time
            and end_time < start_time
        ):
            raise serializers.ValidationError(
                {
                    "end_time": (
                        "End time must be greater than "
                        "or equal to start time."
                    )
                }
            )

        # Validate itinerary date against Trip dates.
        itinerary = self.context.get("itinerary")

        if itinerary and date:
            trip = itinerary.trip

            if date < trip.start_date:
                raise serializers.ValidationError(
                    {
                        "date": (
                            "Itinerary item date cannot be "
                            "before the trip start date."
                        )
                    }
                )

            if date > trip.end_date:
                raise serializers.ValidationError(
                    {
                        "date": (
                            "Itinerary item date cannot be "
                            "after the trip end date."
                        )
                    }
                )

        return attrs