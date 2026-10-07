import logging

from django.db import IntegrityError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.apps.itinerary.serializers import ItineraryItemSerializer
from backend.apps.itinerary.services import ItineraryItemService


logger = logging.getLogger(__name__)


class ItineraryItemListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, itinerary_id):
        try:
            items = ItineraryItemService.get_items(
                user=request.user,
                itinerary_id=itinerary_id,
            )

            serializer = ItineraryItemSerializer(
                items,
                many=True,
            )

            return Response(
                serializer.data,
                status=status.HTTP_200_OK,
            )

        except Exception:
            logger.exception(
                "Unexpected error while retrieving itinerary items."
            )

            return Response(
                {"detail": "Something went wrong."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def post(self, request, itinerary_id):
        itinerary = ItineraryItemService.get_user_itinerary(
            user=request.user,
            itinerary_id=itinerary_id,
        )

        serializer = ItineraryItemSerializer(
            data=request.data,
            context={
                "itinerary": itinerary,
            },
        )

        serializer.is_valid(raise_exception=True)

        try:
            item = ItineraryItemService.create_item(
                user=request.user,
                itinerary_id=itinerary_id,
                validated_data=serializer.validated_data,
            )

            response_serializer = ItineraryItemSerializer(item)

            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED,
            )

        except IntegrityError:
            return Response(
                {
                    "detail": (
                        "An itinerary item with the same "
                        "date and order already exists."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception:
            logger.exception(
                "Unexpected error while creating itinerary item."
            )

            return Response(
                {"detail": "Something went wrong."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ItineraryItemDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, itinerary_id, item_id):
        item = ItineraryItemService.get_item(
            user=request.user,
            itinerary_id=itinerary_id,
            item_id=item_id,
        )

        itinerary = item.itinerary

        serializer = ItineraryItemSerializer(
            item,
            data=request.data,
            partial=True,
            context={
                "itinerary": itinerary,
            },
        )

        serializer.is_valid(raise_exception=True)

        try:
            updated_item = ItineraryItemService.update_item(
                user=request.user,
                itinerary_id=itinerary_id,
                item_id=item_id,
                validated_data=serializer.validated_data,
            )

            response_serializer = ItineraryItemSerializer(
                updated_item
            )

            return Response(
                response_serializer.data,
                status=status.HTTP_200_OK,
            )

        except IntegrityError:
            return Response(
                {
                    "detail": (
                        "An itinerary item with the same "
                        "date and order already exists."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception:
            logger.exception(
                "Unexpected error while updating itinerary item."
            )

            return Response(
                {"detail": "Something went wrong."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def delete(self, request, itinerary_id, item_id):
        try:
            ItineraryItemService.delete_item(
                user=request.user,
                itinerary_id=itinerary_id,
                item_id=item_id,
            )

            return Response(
                status=status.HTTP_204_NO_CONTENT,
            )

        except Exception:
            logger.exception(
                "Unexpected error while deleting itinerary item."
            )

            return Response(
                {"detail": "Something went wrong."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )