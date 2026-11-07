import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  ArrowRight,
  CalendarDays,
  MapPin,
  Pencil,
  Settings2,
  Sparkles,
  Trash2,
  Users,
  Wallet,
} from "lucide-react"
import { lazy, Suspense, useState } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import { toast } from "sonner"

import { deleteTrip, getTrip } from "@/api/trips"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { ErrorState } from "@/components/shared/error-state"
import { LoadingState } from "@/components/shared/loading-state"
import { PageHeader } from "@/components/shared/page-header"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { CurrencyConverter } from "@/features/currency/currency-converter"
import { ExpenseCard } from "@/features/expenses/expense-card"
import { FlightCard } from "@/features/flights/flight-card"
import { HotelCard } from "@/features/hotels/hotel-card"
import { TripFormDialog } from "@/features/trips/trip-form-dialog"
import { WeatherCard } from "@/features/weather/weather-card"
import { getErrorMessage } from "@/lib/api-error"
import {
  formatCurrency,
  formatDateRange,
  tripDayCount,
  tripNightCount,
} from "@/lib/format"
import { queryKeys } from "@/lib/query-keys"

// Leaflet is the single largest dependency in the app. Keeping the map in its
// own chunk means the trip summary, weather and expenses render before it.
const TripMapCard = lazy(() =>
  import("@/features/map/trip-map-card").then((module) => ({
    default: module.TripMapCard,
  })),
)

const planningLinks = [
  {
    title: "Preferences",
    description:
      "Travel style, pace, accommodation and the interests that shape the plan.",
    href: "preferences",
    icon: Settings2,
  },
  {
    title: "Places",
    description:
      "Search verified points of interest from OpenStreetMap around your destination.",
    href: "places",
    icon: MapPin,
  },
  {
    title: "Itinerary",
    description:
      "Generate a draft with AI, then edit every day, time and stop yourself.",
    href: "itinerary",
    icon: Sparkles,
  },
] as const

export function TripDetailPage() {
  const { tripId = "" } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [editOpen, setEditOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)

  const tripQuery = useQuery({
    queryKey: queryKeys.trip(tripId),
    queryFn: () => getTrip(tripId),
    enabled: Boolean(tripId),
  })

  const deleteMutation = useMutation({
    mutationFn: () => deleteTrip(tripId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.trips })
      queryClient.removeQueries({ queryKey: queryKeys.trip(tripId) })
      toast.success("Trip deleted.")
      navigate("/trips", { replace: true })
    },
    onError: (error) => {
      toast.error(getErrorMessage(error))
    },
  })

  if (tripQuery.isPending) {
    return <LoadingState label="Loading trip…" />
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

  const trip = tripQuery.data
  const nights = tripNightCount(trip.start_date, trip.end_date)
  const days = tripDayCount(trip.start_date, trip.end_date)

  return (
    <div className="space-y-8">
      <PageHeader
        backTo="/trips"
        backLabel="All trips"
        title={trip.title}
        description={`${trip.destination} · ${formatDateRange(trip.start_date, trip.end_date)}`}
        actions={
          <>
            <Button asChild>
              <Link to={`/trips/${trip.id}/itinerary`}>
                <Sparkles className="size-4" />
                Open itinerary
              </Link>
            </Button>
            <Button variant="outline" onClick={() => setEditOpen(true)}>
              <Pencil className="size-4" />
              Edit
            </Button>
            <Button
              variant="ghost"
              size="icon"
              aria-label="Delete trip"
              onClick={() => setDeleteOpen(true)}
            >
              <Trash2 className="size-4" />
            </Button>
          </>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-1.5">
              <MapPin className="size-3.5" />
              Destination
            </CardDescription>
            <CardTitle className="text-base">{trip.destination}</CardTitle>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-1.5">
              <CalendarDays className="size-3.5" />
              Duration
            </CardDescription>
            <CardTitle className="text-base">
              {days} {days === 1 ? "day" : "days"} · {nights}{" "}
              {nights === 1 ? "night" : "nights"}
            </CardTitle>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-1.5">
              <Users className="size-3.5" />
              Travellers
            </CardDescription>
            <CardTitle className="text-base">{trip.travelers}</CardTitle>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-1.5">
              <Wallet className="size-3.5" />
              Budget
            </CardDescription>
            <CardTitle className="text-base">
              {formatCurrency(trip.budget, trip.currency)}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <WeatherCard tripId={trip.id} className="lg:col-span-2" />
        <CurrencyConverter
          baseCurrency={trip.currency}
          amount={trip.budget}
        />
      </div>

      <FlightCard trip={trip} />

      <HotelCard trip={trip} />

      <ExpenseCard tripId={trip.id} currency={trip.currency} />

      <div className="grid gap-4 md:grid-cols-3">
        {planningLinks.map((item) => {
          const Icon = item.icon

          return (
            <Link
              key={item.href}
              to={`/trips/${trip.id}/${item.href}`}
              className="group rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <Card className="h-full transition-all group-hover:-translate-y-0.5 group-hover:shadow-md">
                <CardHeader>
                  <span className="mb-2 grid size-9 place-items-center rounded-lg bg-muted text-foreground">
                    <Icon className="size-4" />
                  </span>
                  <CardTitle className="flex items-center justify-between text-base">
                    {item.title}
                    <ArrowRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
                  </CardTitle>
                  <CardDescription>{item.description}</CardDescription>
                </CardHeader>
              </Card>
            </Link>
          )
        })}
      </div>

      <Suspense
        fallback={
          <div
            className="h-96 animate-pulse rounded-xl border bg-muted/40"
            aria-hidden="true"
          />
        }
      >
        <TripMapCard trip={trip} />
      </Suspense>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Trip notes</CardTitle>
          <CardDescription>
            Created {new Date(trip.created_at).toLocaleDateString("en-IN")} ·
            Last updated {new Date(trip.updated_at).toLocaleDateString("en-IN")}
          </CardDescription>
        </CardHeader>
      </Card>

      <TripFormDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        trip={trip}
      />

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Delete this trip?"
        description={`“${trip.title}” and its preferences and itinerary will be permanently deleted.`}
        confirmLabel="Delete trip"
        destructive
        pending={deleteMutation.isPending}
        onConfirm={() => deleteMutation.mutate()}
      />
    </div>
  )
}
