import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { formatDistanceToNow } from "date-fns"
import { Bell, X } from "lucide-react"
import { useState } from "react"
import { useNavigate } from "react-router-dom"

import {
  deleteNotification,
  getUnreadNotificationCount,
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from "@/api/notifications"
import type { Notification } from "@/api/types"
import { Button } from "@/components/ui/button"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { getErrorMessage } from "@/lib/api-error"
import { queryKeys } from "@/lib/query-keys"
import { cn } from "@/lib/utils"

function NotificationSkeleton() {
  return (
    <div className="space-y-2 p-3" aria-hidden="true">
      {[0, 1, 2].map((index) => (
        <div key={index} className="h-14 animate-pulse rounded-lg bg-muted" />
      ))}
    </div>
  )
}

/**
 * Bell with an unread badge.
 *
 * The badge and the list are separate queries: the badge stays cheap and
 * polls, while the list is only fetched once the popover is opened.
 */
export function NotificationBell() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)

  const unreadQuery = useQuery({
    queryKey: queryKeys.notificationUnreadCount,
    queryFn: ({ signal }) => getUnreadNotificationCount(signal),
    staleTime: 30_000,
    refetchInterval: 60_000,
    retry: false,
  })

  const listQuery = useQuery({
    queryKey: queryKeys.notifications(false),
    queryFn: ({ signal }) => listNotifications({ signal }),
    enabled: open,
    staleTime: 15_000,
    retry: false,
  })

  const unread = unreadQuery.data ?? 0

  const refresh = () => {
    void queryClient.invalidateQueries({
      queryKey: queryKeys.notificationUnreadCount,
    })
    void queryClient.invalidateQueries({
      queryKey: queryKeys.notifications(false),
    })
  }

  const readMutation = useMutation({
    mutationFn: markNotificationRead,
    onSuccess: refresh,
  })

  const readAllMutation = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: refresh,
  })

  const deleteMutation = useMutation({
    mutationFn: deleteNotification,
    onSuccess: refresh,
  })

  const handleOpen = (notification: Notification) => {
    if (!notification.is_read) {
      readMutation.mutate(notification.id)
    }

    if (notification.trip) {
      setOpen(false)
      navigate(`/trips/${notification.trip}`)
    }
  }

  const notifications = listQuery.data ?? []

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative ml-1"
          aria-label={
            unread > 0
              ? `Notifications, ${unread} unread`
              : "Notifications"
          }
        >
          <Bell className="size-4" />
          {unread > 0 ? (
            <span className="absolute -right-0.5 -top-0.5 grid h-4 min-w-4 place-items-center rounded-full bg-destructive px-1 text-[10px] font-semibold leading-none text-white">
              {unread > 9 ? "9+" : unread}
            </span>
          ) : null}
        </Button>
      </PopoverTrigger>

      <PopoverContent
        align="end"
        className="w-[22rem] max-w-[calc(100vw-2rem)] p-0"
      >
        <div className="flex items-center justify-between gap-2 border-b px-3 py-2">
          <p className="text-sm font-medium">Notifications</p>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-xs"
            disabled={unread === 0 || readAllMutation.isPending}
            onClick={() => readAllMutation.mutate()}
          >
            {readAllMutation.isPending ? "Marking…" : "Mark all read"}
          </Button>
        </div>

        {listQuery.isPending ? (
          <NotificationSkeleton />
        ) : listQuery.isError ? (
          <div className="space-y-2 px-3 py-6 text-center">
            <p className="text-sm text-muted-foreground">
              {getErrorMessage(listQuery.error)}
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                void listQuery.refetch()
              }}
            >
              Try again
            </Button>
          </div>
        ) : notifications.length === 0 ? (
          <p className="px-3 py-10 text-center text-sm text-muted-foreground">
            You&apos;re all caught up.
          </p>
        ) : (
          <ul className="max-h-80 overflow-y-auto">
            {notifications.map((notification) => (
              <li
                key={notification.id}
                className="relative border-b last:border-b-0"
              >
                <button
                  type="button"
                  className={cn(
                    "block w-full space-y-0.5 py-2.5 pl-3 pr-10 text-left transition-colors hover:bg-muted/60",
                    !notification.is_read && "bg-muted/30",
                  )}
                  onClick={() => handleOpen(notification)}
                >
                  <span className="flex items-center gap-2">
                    {!notification.is_read ? (
                      <span
                        className="size-1.5 shrink-0 rounded-full bg-primary"
                        aria-label="Unread"
                      />
                    ) : null}
                    <span className="truncate text-sm font-medium">
                      {notification.title}
                    </span>
                  </span>

                  <span className="block text-xs text-muted-foreground">
                    {notification.message}
                  </span>

                  <span className="block text-[11px] text-muted-foreground">
                    {notification.trip_title
                      ? `${notification.trip_title} · `
                      : ""}
                    {formatDistanceToNow(new Date(notification.created_at), {
                      addSuffix: true,
                    })}
                  </span>
                </button>

                <Button
                  variant="ghost"
                  size="icon"
                  className="absolute right-1 top-1 size-7 text-muted-foreground"
                  aria-label={`Dismiss ${notification.title}`}
                  disabled={deleteMutation.isPending}
                  onClick={() => deleteMutation.mutate(notification.id)}
                >
                  <X className="size-3.5" />
                </Button>
              </li>
            ))}
          </ul>
        )}
      </PopoverContent>
    </Popover>
  )
}
