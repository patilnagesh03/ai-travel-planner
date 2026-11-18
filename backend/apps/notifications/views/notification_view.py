import logging

from django.http import Http404

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.apps.notifications.serializers import NotificationSerializer
from backend.apps.notifications.services import NotificationService


logger = logging.getLogger(__name__)

TRUTHY = {"1", "true", "yes", "on"}


class NotificationListView(APIView):
    """List the caller's notifications, newest first.

    Reading the list first syncs it, so a reminder about a trip that starts
    tomorrow appears without a cron job or a page that has to ask for it.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        unread_only = (
            request.query_params.get("unread", "").lower() in TRUTHY
        )

        try:
            NotificationService.sync_for_user(request.user)

            notifications = NotificationService.list_for_user(
                user=request.user,
                unread_only=unread_only,
            )

            return Response(
                {
                    "success": True,
                    "message": "Notifications retrieved successfully.",
                    "data": NotificationSerializer(
                        notifications,
                        many=True,
                    ).data,
                },
                status=status.HTTP_200_OK,
            )

        except Exception:
            logger.exception(
                "Unexpected error while retrieving notifications."
            )

            return Response(
                {
                    "success": False,
                    "message": (
                        "Something went wrong while retrieving "
                        "notifications."
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class NotificationUnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            NotificationService.sync_for_user(request.user)

            return Response(
                {
                    "success": True,
                    "message": "Unread count retrieved successfully.",
                    "data": {
                        "unread": NotificationService.unread_count(
                            request.user
                        ),
                    },
                },
                status=status.HTTP_200_OK,
            )

        except Exception:
            logger.exception(
                "Unexpected error while counting notifications."
            )

            return Response(
                {
                    "success": False,
                    "message": (
                        "Something went wrong while counting notifications."
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class NotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id):
        try:
            notification = NotificationService.mark_read(
                user=request.user,
                notification_id=notification_id,
            )

            return Response(
                {
                    "success": True,
                    "message": "Notification marked as read.",
                    "data": NotificationSerializer(notification).data,
                },
                status=status.HTTP_200_OK,
            )

        except Http404:
            raise

        except Exception:
            logger.exception(
                "Unexpected error while marking a notification as read."
            )

            return Response(
                {
                    "success": False,
                    "message": (
                        "Something went wrong while updating the "
                        "notification."
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class NotificationReadAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            updated = NotificationService.mark_all_read(request.user)

            return Response(
                {
                    "success": True,
                    "message": "Notifications marked as read.",
                    "data": {
                        "updated": updated,
                    },
                },
                status=status.HTTP_200_OK,
            )

        except Exception:
            logger.exception(
                "Unexpected error while marking all notifications as read."
            )

            return Response(
                {
                    "success": False,
                    "message": (
                        "Something went wrong while updating notifications."
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class NotificationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, notification_id):
        try:
            NotificationService.delete(
                user=request.user,
                notification_id=notification_id,
            )

            return Response(
                status=status.HTTP_204_NO_CONTENT,
            )

        except Http404:
            raise

        except Exception:
            logger.exception(
                "Unexpected error while deleting a notification."
            )

            return Response(
                {
                    "success": False,
                    "message": (
                        "Something went wrong while deleting the "
                        "notification."
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
