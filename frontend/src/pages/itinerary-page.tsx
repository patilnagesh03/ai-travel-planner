import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  CalendarDays,
  Clock,
  Loader2,
  MapPin,
  MoreHorizontal,
  Pencil,
  Plus,
  Sparkles,
  Trash2,
  WandSparkles,
} from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { useParams } from "react-router-dom"
import { toast } from "sonner"

import { generateItinerary, getAiStatus } from "@/api/ai"
import {
  deleteItinerary,
  deleteItineraryItem,
  getItinerary,
  listItineraryItems,
} from "@/api/itinerary"
import { getTrip } from "@/api/trips"
import type { GenerationPayload, ItineraryItem } from "@/api/types"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { ErrorState } from "@/components/shared/error-state"
import { LoadingState } from "@/components/shared/loading-state"
import { PageHeader } from "@/components/shared/page-header"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { ItineraryDetailsDialog } from "@/features/itinerary/itinerary-details-dialog"
import {
  ACTIVITY_TYPES,
  ItineraryItemDialog,
} from "@/features/itinerary/itinerary-item-dialog"
import {
  getErrorMessage,
  isConflict,
  isNotFound,
} from "@/lib/api-error"
import {
  enumerateDates,
  formatDate,
  formatTimeRange,
  formatWeekday,
  titleCase,
} from "@/lib/format"
import { queryKeys } from "@/lib/query-keys"

function ItineraryItemRow({
  item,
  onEdit,
  onDelete,
}: {
  item: ItineraryItem
  onEdit: (item: ItineraryItem) => void
  onDelete: (item: ItineraryItem) => void
}) {
  const typeLabel =
    ACTIVITY_TYPES.find((type) => type.value === item.activity_type)?.label ??
    titleCase(item.activity_type)

  return (
    <div className="flex gap-3 px-4 py-4 sm:gap-4">
      <span className="mt-0.5 grid size-7 shrink-0 place-items-center rounded-full bg-muted text-xs font-semibold text-muted-foreground">
        {item.order}
      </span>

      <div className="min-w-0 flex-1 space-y-1.5">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="font-medium leading-snug">{item.title}</h3>
          <Badge variant="secondary">{typeLabel}</Badge>
        </div>

        {item.start_time || item.end_time ? (
          <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <Clock className="size-3.5" />
            {formatTimeRange(item.start_time, item.end_time)}
          </p>
        ) : null}

        {item.location_name || item.location_address ? (
          <p className="flex items-start gap-1.5 text-sm text-muted-foreground">
            <MapPin className="mt-0.5 size-3.5 shrink-0" />
            <span>
              {item.location_name}
              {item.location_name && item.location_address ? " · " : ""}
              {item.location_address}
            </span>
          </p>
        ) : null}

        {item.description ? (
          <p className="text-sm text-muted-foreground">{item.description}</p>
        ) : null}
      </div>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label={`Actions for ${item.title}`}
          >
            <MoreHorizontal className="size-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onSelect={() => onEdit(item)}>
            <Pencil className="size-4" />
            Edit activity
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            variant="destructive"
            onSelect={() => onDelete(item)}
          >
            <Trash2 className="size-4" />
            Delete activity
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  )
}

export function ItineraryPage() {
  const { tripId = "" } = useParams()
  const queryClient = useQueryClient()

  const [itemDialogOpen, setItemDialogOpen] = useState(false)
  const [editingItem, setEditingItem] = useState<ItineraryItem | undefined>()
  const [defaultItemDate, setDefaultItemDate] = useState<string | undefined>()
  const [deletingItem, setDeletingItem] = useState<ItineraryItem | null>(null)
  const [detailsOpen, setDetailsOpen] = useState(false)
  const [deleteItineraryOpen, setDeleteItineraryOpen] = useState(false)
  const [replaceOpen, setReplaceOpen] = useState(false)
  const [generationElapsed, setGenerationElapsed] = useState(0)

  const tripQuery = useQuery({
    queryKey: queryKeys.trip(tripId),
    queryFn: () => getTrip(tripId),
    enabled: Boolean(tripId),
  })

  const itineraryQuery = useQuery({
    queryKey: queryKeys.itinerary(tripId),
    queryFn: async () => {
      try {
        return await getItinerary(tripId)
      } catch (error) {
        if (isNotFound(error)) {
          return null
        }

        throw error
      }
    },
    enabled: Boolean(tripId),
  })

  const itinerary = itineraryQuery.data ?? null
  const itineraryId = itinerary?.id ?? ""

  const itemsQuery = useQuery({
    queryKey: queryKeys.itineraryItems(itineraryId || "none"),
    queryFn: () => listItineraryItems(itineraryId),
    enabled: Boolean(itineraryId),
  })

  const items = useMemo(() => itemsQuery.data ?? [], [itemsQuery.data])

  const aiStatusQuery = useQuery({
    queryKey: queryKeys.aiStatus,
    queryFn: getAiStatus,
    retry: false,
    staleTime: 60_000,
    enabled: !itinerary && itineraryQuery.isSuccess,
  })

  const trip = tripQuery.data

  const days = useMemo(() => {
    if (!trip) {
      return []
    }

    return enumerateDates(trip.start_date, trip.end_date).map((date) => ({
      date,
      items: items
        .filter((item) => item.date === date)
        .sort(
          (left, right) =>
            left.order - right.order ||
            (left.start_time ?? "").localeCompare(right.start_time ?? ""),
        ),
    }))
  }, [trip, items])

  const generationMutation = useMutation({
    mutationFn: (payload: GenerationPayload) =>
      generateItinerary(tripId, payload),
    onSuccess: (result) => {
      setReplaceOpen(false)
      void queryClient.invalidateQueries({
        queryKey: queryKeys.itinerary(tripId),
      })

      if (result.itinerary_id) {
        void queryClient.invalidateQueries({
          queryKey: queryKeys.itineraryItems(result.itinerary_id),
        })
      }

      toast.success(
        result.persisted
          ? "Itinerary generated and saved."
          : "Itinerary generated.",
      )
    },
    onError: (error) => {
      // A failed run must not leave the replace prompt sitting over the page:
      // the toast is the feedback, and the current itinerary is untouched.
      setReplaceOpen(false)

      if (isConflict(error)) {
        setReplaceOpen(true)
        toast.info("An itinerary already exists for this trip.")
        return
      }

      toast.error(getErrorMessage(error))
    },
  })

  useEffect(() => {
    if (!generationMutation.isPending) {
      setGenerationElapsed(0)
      return
    }

    const startedAt = Date.now()

    const timer = window.setInterval(() => {
      setGenerationElapsed(Math.floor((Date.now() - startedAt) / 1000))
    }, 1000)

    return () => {
      window.clearInterval(timer)
    }
  }, [generationMutation.isPending])

  const deleteItineraryMutation = useMutation({
    mutationFn: () => deleteItinerary(tripId),
    onSuccess: () => {
      queryClient.setQueryData(queryKeys.itinerary(tripId), null)

      if (itineraryId) {
        queryClient.removeQueries({
          queryKey: queryKeys.itineraryItems(itineraryId),
        })
      }

      setDeleteItineraryOpen(false)
      toast.success("Itinerary deleted.")
    },
    onError: (error) => {
      toast.error(getErrorMessage(error))
    },
  })

  const deleteItemMutation = useMutation({
    mutationFn: (item: ItineraryItem) =>
      deleteItineraryItem(itineraryId, item.id),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.itineraryItems(itineraryId),
      })
      setDeletingItem(null)
      toast.success("Activity deleted.")
    },
    onError: (error) => {
      toast.error(getErrorMessage(error))
    },
  })

  if (tripQuery.isPending || itineraryQuery.isPending) {
    return <LoadingState label="Loading itinerary…" />
  }

  if (tripQuery.isError) {
    return (
      <ErrorState
        title="Trip unavailable"
        message={getErrorMessage(tripQuery.error)}
        onRetry={() => {
          void tripQuery.refetch()
        }}
      />
    )
  }

  if (itineraryQuery.isError) {
    return (
      <ErrorState
        title="Itinerary unavailable"
        message={getErrorMessage(itineraryQuery.error)}
        onRetry={() => {
          void itineraryQuery.refetch()
        }}
      />
    )
  }

  if (!trip) {
    return null
  }

  if (itinerary && itemsQuery.isPending) {
    return <LoadingState label="Loading activities…" />
  }

  if (itinerary && itemsQuery.isError) {
    return (
      <ErrorState
        title="Activities unavailable"
        message={getErrorMessage(itemsQuery.error)}
        onRetry={() => {
          void itemsQuery.refetch()
        }}
      />
    )
  }

  const openAddItem = (date?: string) => {
    setEditingItem(undefined)
    setDefaultItemDate(date ?? trip.start_date)
    setItemDialogOpen(true)
  }

  const openEditItem = (item: ItineraryItem) => {
    setEditingItem(item)
    setDefaultItemDate(item.date)
    setItemDialogOpen(true)
  }

  const handleGenerate = () => {
    if (itinerary) {
      setReplaceOpen(true)
      return
    }

    generationMutation.mutate({ dry_run: false, replace: false })
  }

  const aiStatus = aiStatusQuery.data

  return (
    <div className="space-y-8">
      <PageHeader
        backTo={`/trips/${trip.id}`}
        backLabel={trip.title}
        title={itinerary?.title ?? "Itinerary"}
        description={
          itinerary?.description ??
          `${trip.destination} · ${formatDate(trip.start_date)} – ${formatDate(trip.end_date)}`
        }
        actions={
          itinerary ? (
            <>
              <Button onClick={() => openAddItem()}>
                <Plus className="size-4" />
                Add activity
              </Button>
              <Button variant="outline" onClick={() => setDetailsOpen(true)}>
                <Pencil className="size-4" />
                Edit details
              </Button>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Delete itinerary"
                onClick={() => setDeleteItineraryOpen(true)}
              >
                <Trash2 className="size-4" />
              </Button>
            </>
          ) : undefined
        }
      />

      {generationMutation.isPending ? (
        <Card className="border-primary/30 bg-primary/5">
          <CardContent className="flex flex-col items-center gap-4 py-12 text-center">
            <Loader2 className="size-7 animate-spin text-primary" />
            <div className="space-y-1">
              <h2 className="font-medium">Generating your itinerary…</h2>
              <p className="text-sm text-muted-foreground">
                Elapsed: {generationElapsed}s. A full generation usually takes
                60–130 seconds.
              </p>
            </div>
            <p className="max-w-md text-xs text-muted-foreground">
              The planner is searching real places and waiting for the local
              model. There is no streaming, so results arrive all at once.
            </p>
          </CardContent>
        </Card>
      ) : null}

      {!itinerary ? (
        <>
          <Card className="overflow-hidden border-primary/20">
            <CardContent className="space-y-5 py-10">
              <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-center">
                <span className="grid size-12 place-items-center rounded-full bg-primary/10 text-primary">
                  <WandSparkles className="size-6" />
                </span>
                <div className="space-y-1">
                  <h2 className="text-lg font-medium">
                    Let the planner draft your days
                  </h2>
                  <p className="max-w-2xl text-sm text-muted-foreground">
                    The planner finds real places around {trip.destination},
                    asks the local model to arrange them, and drops anything it
                    cannot verify. You can edit every activity afterwards.
                  </p>
                </div>
              </div>

              {aiStatus ? (
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <Badge
                    variant={aiStatus.available ? "secondary" : "outline"}
                    className={
                      aiStatus.available
                        ? "bg-emerald-500/10 text-emerald-700"
                        : "border-amber-500/30 text-amber-700"
                    }
                  >
                    {aiStatus.available ? "Model online" : "Model offline"}
                  </Badge>
                  <span className="text-muted-foreground">
                    {aiStatus.provider} · {aiStatus.model}
                  </span>
                </div>
              ) : null}

              {aiStatus && !aiStatus.available ? (
                <p className="rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-sm text-amber-800">
                  The AI provider is not reachable. Start Ollama, or create an
                  itinerary manually and add activities yourself.
                </p>
              ) : null}

              <div className="flex flex-wrap gap-2">
                <Button
                  onClick={handleGenerate}
                  disabled={generationMutation.isPending}
                >
                  <Sparkles className="size-4" />
                  Generate with AI
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setDetailsOpen(true)}
                  disabled={generationMutation.isPending}
                >
                  <Plus className="size-4" />
                  Create manually
                </Button>
              </div>
            </CardContent>
          </Card>

          <div className="flex items-start gap-3 rounded-xl border bg-muted/40 px-4 py-3 text-sm">
            <CalendarDays className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
            <p className="text-muted-foreground">
              A destination must match the curated Indian city list for
              generation to work. Places come from OpenStreetMap, so the first
              run can be slow.
            </p>
          </div>
        </>
      ) : null}

      {itinerary ? (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-muted-foreground">
              {items.length} {items.length === 1 ? "activity" : "activities"} ·{" "}
              {days.length} {days.length === 1 ? "day" : "days"}
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={handleGenerate}
              disabled={generationMutation.isPending}
            >
              <Sparkles className="size-4" />
              Regenerate with AI
            </Button>
          </div>

          {days.map((day) => (
            <Card key={day.date}>
              <CardHeader className="border-b">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="space-y-1">
                    <CardTitle className="text-base">
                      {formatWeekday(day.date)}, {formatDate(day.date)}
                    </CardTitle>
                    <CardDescription>
                      {day.items.length}{" "}
                      {day.items.length === 1 ? "activity" : "activities"}
                    </CardDescription>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => openAddItem(day.date)}
                  >
                    <Plus className="size-4" />
                    Add activity
                  </Button>
                </div>
              </CardHeader>

              <CardContent className="p-0">
                {day.items.length === 0 ? (
                  <p className="px-4 py-6 text-sm text-muted-foreground">
                    Nothing planned for this day yet.
                  </p>
                ) : (
                  <div className="divide-y">
                    {day.items.map((item) => (
                      <ItineraryItemRow
                        key={item.id}
                        item={item}
                        onEdit={openEditItem}
                        onDelete={setDeletingItem}
                      />
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      ) : null}

      <ItineraryDetailsDialog
        open={detailsOpen}
        onOpenChange={setDetailsOpen}
        trip={trip}
        itinerary={itinerary ?? undefined}
      />

      {itinerary ? (
        <ItineraryItemDialog
          open={itemDialogOpen}
          onOpenChange={(open) => {
            setItemDialogOpen(open)

            if (!open) {
              setEditingItem(undefined)
            }
          }}
          itineraryId={itinerary.id}
          trip={trip}
          items={items}
          item={editingItem}
          defaultDate={defaultItemDate}
        />
      ) : null}

      <ConfirmDialog
        open={deletingItem !== null}
        onOpenChange={(open) => {
          if (!open) {
            setDeletingItem(null)
          }
        }}
        title="Delete this activity?"
        description={
          deletingItem
            ? `“${deletingItem.title}” will be removed from the itinerary.`
            : ""
        }
        confirmLabel="Delete activity"
        destructive
        pending={deleteItemMutation.isPending}
        onConfirm={() => {
          if (deletingItem) {
            deleteItemMutation.mutate(deletingItem)
          }
        }}
      />

      <ConfirmDialog
        open={deleteItineraryOpen}
        onOpenChange={setDeleteItineraryOpen}
        title="Delete this itinerary?"
        description="The itinerary and every activity in it will be permanently deleted. The trip itself stays."
        confirmLabel="Delete itinerary"
        destructive
        pending={deleteItineraryMutation.isPending}
        onConfirm={() => deleteItineraryMutation.mutate()}
      />

      <ConfirmDialog
        open={replaceOpen}
        onOpenChange={setReplaceOpen}
        title="Replace the current itinerary?"
        description="Generation deletes the existing itinerary and its activities, then creates a new one. It can take 60–130 seconds."
        confirmLabel="Replace and generate"
        destructive
        pending={generationMutation.isPending}
        onConfirm={() =>
          generationMutation.mutate({ dry_run: false, replace: true })
        }
      />
    </div>
  )
}
