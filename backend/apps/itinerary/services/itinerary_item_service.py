from django.db import transaction
from django.shortcuts import get_object_or_404

from backend.apps.itinerary.models import Itinerary, ItineraryItem


class ItineraryItemService:

    @staticmethod
    def get_user_itinerary(user, itinerary_id):
        return get_object_or_404(
            Itinerary,
            id=itinerary_id,
            trip__user=user,
        )

    @staticmethod
    @transaction.atomic
    def create_item(user, itinerary_id, validated_data):
        itinerary = ItineraryItemService.get_user_itinerary(
            user=user,
            itinerary_id=itinerary_id,
        )

        item = ItineraryItem.objects.create(
            itinerary=itinerary,
            **validated_data,
        )

        return item

    @staticmethod
    def get_items(user, itinerary_id):
        itinerary = ItineraryItemService.get_user_itinerary(
            user=user,
            itinerary_id=itinerary_id,
        )

        return (
            ItineraryItem.objects
            .filter(itinerary=itinerary)
            .order_by("date", "order", "start_time")
        )

    @staticmethod
    def get_item(user, itinerary_id, item_id):
        itinerary = ItineraryItemService.get_user_itinerary(
            user=user,
            itinerary_id=itinerary_id,
        )

        return get_object_or_404(
            ItineraryItem,
            id=item_id,
            itinerary=itinerary,
        )

    @staticmethod
    @transaction.atomic
    def update_item(
        user,
        itinerary_id,
        item_id,
        validated_data,
    ):
        itinerary = ItineraryItemService.get_user_itinerary(
            user=user,
            itinerary_id=itinerary_id,
        )

        item = get_object_or_404(
            ItineraryItem,
            id=item_id,
            itinerary=itinerary,
        )

        for field, value in validated_data.items():
            setattr(item, field, value)

        item.save()

        return item

    @staticmethod
    @transaction.atomic
    def delete_item(user, itinerary_id, item_id):
        itinerary = ItineraryItemService.get_user_itinerary(
            user=user,
            itinerary_id=itinerary_id,
        )

        item = get_object_or_404(
            ItineraryItem,
            id=item_id,
            itinerary=itinerary,
        )

        item.delete()