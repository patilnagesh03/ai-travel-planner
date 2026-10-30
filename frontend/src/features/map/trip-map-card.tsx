import { useQuery } from "@tanstack/react-query"
import { ExternalLink, MapPinned } from "lucide-react"
import { useMemo } from "react"

import { getItinerary, listItineraryItems } from "@/api/itinerary"
import { resolveDestination } from "@/api/places"
import type { Trip } from "@/api/types"
import { LoadingState } from "@/components/shared/loading-state"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { MapPanel, type MapMarker } from "@/features/map/map-panel"
import { getErrorMessage, isNotFound } from "@/lib/api-error"
import { queryKeys } from "@/lib/query-keys"
import { cn } from "@/lib/utils"

export function TripMapCard({
  trip,
  className,
}: {
  trip: Trip
  className?: string
}) {
  // The backend owns the spelling/alias rules, so the map reuses the same
  // resolution as place search instead of bundling its own city list.
  const destinationQuery = useQuery({
    queryKey: queryKeys.resolvedDestination(trip.destination),
    queryFn: ({ signal }) => resolveDestination(trip.destination, signal),
    staleTime: 10 * 60_000,
    retry: false,
  })

  const itineraryQuery = useQuery({
    queryKey: queryKeys.itinerary(trip.id),
    queryFn: async () => {
      try {
        return await getItinerary(trip.id)
      } catch (error) {
        if (isNotFound(error)) {
          return null
        }

        throw error
      }
    },
    enabled: Boolean(trip.id),
  })

  const itineraryId = itineraryQuery.data?.id ?? ""

  const itemsQuery = useQuery({
    queryKey: queryKeys.itineraryItems(itineraryId || "none"),
    queryFn: () => listItineraryItems(itineraryId),
    enabled: Boolean(itineraryId),
  })

  const items = useMemo(() => itemsQuery.data ?? [], [itemsQuery.data])

  const markers = useMemo<MapMarker[]>(() => {
    const result: MapMarker[] = []

    if (destinationQuery.data) {
      result.push({
        id: "destination",
        latitude: destinationQuery.data.latitude,
        longitude: destinationQuery.data.longitude,
        title: destinationQuery.data.name,
        description: destinationQuery.data.state,
        emphasis: true,
      })
    }

    for (const item of items) {
      if (item.latitude === null || item.longitude === null) {
        continue
      }

      const latitude = Number(item.latitude)
      const longitude = Number(item.longitude)

      if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
        continue
      }

      result.push({
        id: `item-${item.id}`,
        latitude,
        longitude,
        title: item.location_name || item.title,
        description: item.location_name ? item.title : item.date,
      })
    }

    return result
  }, [destinationQuery.data, items])

  const stopCount = markers.length - (destinationQuery.data ? 1 : 0)

  const openStreetMapUrl = destinationQuery.data
    ? `https://www.openstreetmap.org/#map=12/${destinationQuery.data.latitude}/${destinationQuery.data.longitude}`
    : null

  return (
    <Card className={cn(className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <MapPinned className="size-4" />
          Map
        </CardTitle>
        <CardDescription>
          {destinationQuery.data
            ? `${destinationQuery.data.name}, ${destinationQuery.data.state}`
            : trip.destination}
          {stopCount > 0
            ? ` · ${stopCount} ${stopCount === 1 ? "saved stop" : "saved stops"}`
            : " · destination overview"}
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-3">
        {destinationQuery.isPending ? (
          <LoadingState label="Finding the destination…" className="py-16" />
        ) : destinationQuery.isError ? (
          <div className="flex flex-col items-start gap-3 rounded-lg border border-dashed px-4 py-6 text-sm">
            <p className="text-muted-foreground">
              {getErrorMessage(destinationQuery.error)}
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                void destinationQuery.refetch()
              }}
            >
              Try again
            </Button>
          </div>
        ) : destinationQuery.data ? (
          <MapPanel
            center={{
              latitude: destinationQuery.data.latitude,
              longitude: destinationQuery.data.longitude,
            }}
            markers={markers}
            height={340}
            ariaLabel={`Map of ${destinationQuery.data.name}`}
          />
        ) : null}

        <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
          <span>
            {stopCount > 0
              ? "Blue marks the destination; teal circles are itinerary stops with coordinates."
              : "Itinerary stops with coordinates appear here once you add them."}
          </span>
          {openStreetMapUrl ? (
            <a
              href={openStreetMapUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 font-medium text-foreground underline-offset-4 hover:underline"
            >
              Open larger map
              <ExternalLink className="size-3" />
            </a>
          ) : null}
        </div>
      </CardContent>
    </Card>
  )
}
