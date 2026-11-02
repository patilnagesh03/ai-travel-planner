import { api } from "@/api/client"
import type {
  ApiEnvelope,
  Notification,
  ReadAllNotificationsResult,
  UnreadNotificationCount,
} from "@/api/types"
import { unwrap } from "@/lib/envelope"

const NOTIFICATION_TIMEOUT = 15_000

export async function listNotifications(
  options: { unreadOnly?: boolean; signal?: AbortSignal } = {},
): Promise<Notification[]> {
  const { unreadOnly = false, signal } = options

  const response = await api.get<ApiEnvelope<Notification[]>>(
    "/api/v1/notifications/",
    {
      signal,
      timeout: NOTIFICATION_TIMEOUT,
      params: unreadOnly ? { unread: "true" } : undefined,
    },
  )

  return unwrap(response.data)
}

export async function getUnreadNotificationCount(
  signal?: AbortSignal,
): Promise<number> {
  const response = await api.get<ApiEnvelope<UnreadNotificationCount>>(
    "/api/v1/notifications/unread-count/",
    { signal, timeout: NOTIFICATION_TIMEOUT },
  )

  return unwrap(response.data).unread
}

export async function markNotificationRead(
  notificationId: string,
): Promise<Notification> {
  const response = await api.post<ApiEnvelope<Notification>>(
    `/api/v1/notifications/${notificationId}/read/`,
  )

  return unwrap(response.data)
}

export async function markAllNotificationsRead(): Promise<number> {
  const response = await api.post<ApiEnvelope<ReadAllNotificationsResult>>(
    "/api/v1/notifications/read-all/",
  )

  return unwrap(response.data).updated
}

export async function deleteNotification(
  notificationId: string,
): Promise<void> {
  await api.delete(`/api/v1/notifications/${notificationId}/`)
}
