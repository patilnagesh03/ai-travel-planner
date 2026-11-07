import { useQuery } from "@tanstack/react-query"
import { ExternalLink, Plane } from "lucide-react"

import { getTripFlightLinks } from "@/api/flights"
import type { Trip } from "@/api/types"
import { ErrorState } from "@/components/shared/error-state"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { getErrorMessage } from "@/lib/api-error"
import { queryKeys } from "@/lib/query-keys"
import { cn } from "@/lib/utils"

export function FlightCard({
  trip,
  className,
}: {
  trip: Trip
  className?: string
}) {
  const hasOrigin = trip.origin.trim().length > 0

  const flightQuery = useQuery({
    queryKey: queryKeys.flights(trip.id),
    queryFn: ({ signal }) => getTripFlightLinks(trip.id, signal),
    enabled: Boolean(trip.id) && hasOrigin,
    // The result depends only on the trip, so it cannot go stale on its own.
    staleTime: 30 * 60_000,
  })

  return (
    <Card className={cn(className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Plane className="size-4" />
          Flights
        </CardTitle>
        <CardDescription>
          {hasOrigin
            ? `${trip.origin} → ${trip.destination}`
            : "Add a departure city to see flight search links"}
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-3">
        {!hasOrigin ? (
          <p className="rounded-lg border border-dashed px-4 py-6 text-sm text-muted-foreground">
            Edit this trip and fill in the departure city. We use it to build a
            route on Google Flights and Kayak; no fare data is fetched here.
          </p>
        ) : flightQuery.isPending ? (
          <div className="grid gap-2 sm:grid-cols-2" aria-hidden="true">
            <div className="h-16 animate-pulse rounded-lg bg-muted" />
            <div className="h-16 animate-pulse rounded-lg bg-muted" />
          </div>
        ) : flightQuery.isError ? (
          <ErrorState
            title="Flight links unavailable"
            message={getErrorMessage(flightQuery.error)}
            onRetry={() => {
              void flightQuery.refetch()
            }}
          />
        ) : (
          <>
            <div className="grid gap-2 sm:grid-cols-2">
              {flightQuery.data.links.map((link) => (
                <a
                  key={link.provider}
                  href={link.url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center justify-between gap-2 rounded-lg border px-3 py-2.5 text-sm transition-colors hover:border-foreground/30 hover:bg-muted/50"
                >
                  <span className="font-medium">{link.label}</span>
                  <ExternalLink className="size-3.5 text-muted-foreground" />
                </a>
              ))}
            </div>

            <p className="text-[11px] text-muted-foreground">
              {flightQuery.data.disclaimer}
            </p>
          </>
        )}
      </CardContent>
    </Card>
  )
}
