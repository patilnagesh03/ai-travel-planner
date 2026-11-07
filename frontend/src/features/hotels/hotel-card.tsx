import { useQuery } from "@tanstack/react-query"
import { BedDouble, ExternalLink, Loader2, MapPin } from "lucide-react"

import { getTripHotels } from "@/api/hotels"
import type { Hotel, PlaceCategory, Trip } from "@/api/types"
import { ErrorState } from "@/components/shared/error-state"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { getErrorMessage } from "@/lib/api-error"
import { queryKeys } from "@/lib/query-keys"
import { cn } from "@/lib/utils"

const HOTEL_CATEGORY_LABELS: Partial<Record<PlaceCategory, string>> = {
  hotel: "Hotel",
  guest_house: "Guest house",
  hostel: "Hostel",
  apartment: "Apartment",
}

function HotelRow({ hotel }: { hotel: Hotel }) {
  const mapUrl = `https://www.openstreetmap.org/?mlat=${hotel.latitude}&mlon=${hotel.longitude}#map=17/${hotel.latitude}/${hotel.longitude}`

  return (
    <div className="rounded-lg border p-3 text-sm">
      <div className="flex items-start justify-between gap-2">
        <p className="font-medium leading-snug">{hotel.name}</p>
        <Badge variant="secondary">
          {HOTEL_CATEGORY_LABELS[hotel.category] ?? "Stay"}
        </Badge>
      </div>

      <p className="mt-1 flex items-start gap-1.5 text-xs text-muted-foreground">
        <MapPin className="mt-0.5 size-3 shrink-0" />
        <span>{hotel.address || "No address in the source data."}</span>
      </p>

      <div className="mt-2 flex items-center justify-between gap-2 border-t pt-2 text-xs">
        <span className="text-muted-foreground">
          {hotel.distance_km.toFixed(1)} km from the centre
        </span>
        <a
          href={mapUrl}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 font-medium underline-offset-4 hover:underline"
        >
          Map
          <ExternalLink className="size-3" />
        </a>
      </div>
    </div>
  )
}

export function HotelCard({
  trip,
  className,
}: {
  trip: Trip
  className?: string
}) {
  const hotelQuery = useQuery({
    queryKey: queryKeys.hotels(trip.id),
    queryFn: ({ signal }) => getTripHotels(trip.id, signal),
    enabled: Boolean(trip.id),
    retry: false,
    // The backend caches the provider response for 10 minutes.
    staleTime: 10 * 60_000,
  })

  const result = hotelQuery.data

  return (
    <Card className={cn(className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <BedDouble className="size-4" />
          Where to stay
        </CardTitle>
        <CardDescription>
          {result
            ? `Accommodation near ${result.destination.name}, closest first`
            : "Accommodation from OpenStreetMap, closest to the centre first"}
        </CardDescription>

        {result ? (
          <CardAction>
            <Button asChild size="sm" variant="outline">
              <a href={result.booking_url} target="_blank" rel="noreferrer">
                Live prices
                <ExternalLink className="size-3.5" />
              </a>
            </Button>
          </CardAction>
        ) : null}
      </CardHeader>

      <CardContent className="space-y-3">
        {hotelQuery.isPending ? (
          <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed px-4 py-10 text-center">
            <Loader2 className="size-6 animate-spin text-muted-foreground" />
            <div className="space-y-1">
              <p className="text-sm font-medium">Searching OpenStreetMap…</p>
              <p className="text-xs text-muted-foreground">
                This usually takes 20–40 seconds on the first search.
              </p>
            </div>
          </div>
        ) : hotelQuery.isError ? (
          <ErrorState
            title="Accommodation unavailable"
            message={getErrorMessage(hotelQuery.error)}
            onRetry={() => {
              void hotelQuery.refetch()
            }}
          />
        ) : result && result.hotels.length > 0 ? (
          <>
            <div className="grid gap-3 sm:grid-cols-2">
              {result.hotels.map((hotel) => (
                <HotelRow
                  key={`${hotel.source}-${hotel.source_id}`}
                  hotel={hotel}
                />
              ))}
            </div>

            <p className="text-[11px] text-muted-foreground">
              {result.attribution}
            </p>
          </>
        ) : result ? (
          <div className="flex flex-col gap-3 rounded-lg border border-dashed px-4 py-8 text-center">
            <p className="mx-auto max-w-md text-sm text-muted-foreground">
              No mapped accommodation was found near {result.destination.name}.
              Search live availability instead.
            </p>
            <Button asChild size="sm" variant="outline" className="mx-auto">
              <a href={result.booking_url} target="_blank" rel="noreferrer">
                Check Booking.com
                <ExternalLink className="size-3.5" />
              </a>
            </Button>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
