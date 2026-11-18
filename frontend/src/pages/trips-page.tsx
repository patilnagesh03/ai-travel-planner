import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Compass, Plus } from "lucide-react"
import { useEffect, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { toast } from "sonner"

import { deleteTrip, listTrips } from "@/api/trips"
import type { Trip } from "@/api/types"
import { EmptyState } from "@/components/shared/empty-state"
import { ErrorState } from "@/components/shared/error-state"
import { PageHeader } from "@/components/shared/page-header"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { TripCard } from "@/features/trips/trip-card"
import { TripFormDialog } from "@/features/trips/trip-form-dialog"
import { getErrorMessage } from "@/lib/api-error"
import { queryKeys } from "@/lib/query-keys"

export function TripsPage() {
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()

  const [createOpen, setCreateOpen] = useState(false)
  const [editingTrip, setEditingTrip] = useState<Trip | null>(null)
  const [deletingTrip, setDeletingTrip] = useState<Trip | null>(null)

  useEffect(() => {
    if (searchParams.get("new") === "1") {
      setCreateOpen(true)

      const nextParams = new URLSearchParams(searchParams)
      nextParams.delete("new")
      setSearchParams(nextParams, { replace: true })
    }
  }, [searchParams, setSearchParams])

  const tripsQuery = useQuery({
    queryKey: queryKeys.trips,
    queryFn: listTrips,
  })

  const deleteMutation = useMutation({
    mutationFn: (trip: Trip) => deleteTrip(trip.id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.trips })
      setDeletingTrip(null)
      toast.success("Trip deleted.")
    },
    onError: (error) => {
      toast.error(getErrorMessage(error))
    },
  })

  return (
    <div className="space-y-8">
      <PageHeader
        title="Your trips"
        description="Every trip keeps its own preferences, places and editable itinerary."
        actions={
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="size-4" />
            New trip
          </Button>
        }
      />

      {tripsQuery.isPending ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <Skeleton key={index} className="h-56 rounded-xl" />
          ))}
        </div>
      ) : tripsQuery.isError ? (
        <ErrorState
          message={getErrorMessage(tripsQuery.error)}
          onRetry={() => {
            void tripsQuery.refetch()
          }}
        />
      ) : tripsQuery.data.length === 0 ? (
        <EmptyState
          icon={<Compass className="size-6" />}
          title="No trips yet"
          description="Create your first trip, add a few preferences, and let the planner draft an itinerary."
          action={
            <Button onClick={() => setCreateOpen(true)}>
              <Plus className="size-4" />
              Create your first trip
            </Button>
          }
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {tripsQuery.data.map((trip) => (
            <TripCard
              key={trip.id}
              trip={trip}
              onEdit={setEditingTrip}
              onDelete={setDeletingTrip}
            />
          ))}
        </div>
      )}

      <TripFormDialog open={createOpen} onOpenChange={setCreateOpen} />

      <TripFormDialog
        open={editingTrip !== null}
        onOpenChange={(open) => {
          if (!open) {
            setEditingTrip(null)
          }
        }}
        trip={editingTrip ?? undefined}
      />

      <ConfirmDialog
        open={deletingTrip !== null}
        onOpenChange={(open) => {
          if (!open) {
            setDeletingTrip(null)
          }
        }}
        title="Delete this trip?"
        description={
          deletingTrip
            ? `“${deletingTrip.title}” and its preferences and itinerary will be permanently deleted.`
            : ""
        }
        confirmLabel="Delete trip"
        destructive
        pending={deleteMutation.isPending}
        onConfirm={() => {
          if (deletingTrip) {
            deleteMutation.mutate(deletingTrip)
          }
        }}
      />
    </div>
  )
}
