import { useQuery } from "@tanstack/react-query"
import {
  Clock,
  Compass,
  ExternalLink,
  Info,
  Loader2,
  MapPin,
  Search,
  SlidersHorizontal,
} from "lucide-react"
import { useEffect, useState } from "react"
import { useParams } from "react-router-dom"

import {
  listSupportedDestinations,
  searchPlaces,
} from "@/api/places"
import { getTrip } from "@/api/trips"
import type { Place, PlaceCategory, PlaceSearchParams } from "@/api/types"
import { EmptyState } from "@/components/shared/empty-state"
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
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { getErrorMessage } from "@/lib/api-error"
import { queryKeys } from "@/lib/query-keys"
import { cn } from "@/lib/utils"

const CATEGORIES: { value: PlaceCategory; label: string }[] = [
  { value: "attraction", label: "Attractions" },
  { value: "museum", label: "Museums" },
  { value: "viewpoint", label: "Viewpoints" },
  { value: "monument", label: "Monuments" },
  { value: "religious_site", label: "Religious sites" },
  { value: "park", label: "Parks" },
  { value: "restaurant", label: "Restaurants" },
  { value: "cafe", label: "Cafés" },
]

function categoryLabel(category: PlaceCategory): string {
  return CATEGORIES.find((entry) => entry.value === category)?.label ?? category
}

function PlaceCard({ place }: { place: Place }) {
  const mapUrl = `https://www.openstreetmap.org/?mlat=${place.latitude}&mlon=${place.longitude}#map=17/${place.latitude}/${place.longitude}`

  return (
    <Card className="flex flex-col">
      <CardHeader className="gap-2 pb-3">
        <div className="flex items-start justify-between gap-3">
          <CardTitle className="text-base leading-snug">{place.name}</CardTitle>
          <Badge variant="secondary">{categoryLabel(place.category)}</Badge>
        </div>
        <CardDescription className="flex items-start gap-1.5">
          <MapPin className="mt-0.5 size-3.5 shrink-0" />
          <span>{place.address || "No address in the source data."}</span>
        </CardDescription>
      </CardHeader>

      <CardContent className="mt-auto space-y-3 text-sm">
        {place.opening_hours ? (
          <p className="flex items-start gap-1.5 text-muted-foreground">
            <Clock className="mt-0.5 size-3.5 shrink-0" />
            <span>{place.opening_hours}</span>
          </p>
        ) : null}

        <div className="flex items-center justify-between gap-3 border-t pt-3">
          <span className="text-xs text-muted-foreground">
            {place.latitude.toFixed(4)}, {place.longitude.toFixed(4)}
          </span>
          <a
            href={mapUrl}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-xs font-medium underline-offset-4 hover:underline"
          >
            View on map
            <ExternalLink className="size-3" />
          </a>
        </div>
      </CardContent>
    </Card>
  )
}

export function PlacesPage() {
  const { tripId = "" } = useParams()

  const [destination, setDestination] = useState("")
  const [radius, setRadius] = useState("10")
  const [limit, setLimit] = useState("20")
  const [selectedCategories, setSelectedCategories] = useState<PlaceCategory[]>(
    [],
  )
  const [searchParams, setSearchParams] = useState<PlaceSearchParams | null>(
    null,
  )
  const [formError, setFormError] = useState<string | null>(null)
  const [destinationPickerOpen, setDestinationPickerOpen] = useState(false)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)

  const tripQuery = useQuery({
    queryKey: queryKeys.trip(tripId),
    queryFn: () => getTrip(tripId),
    enabled: Boolean(tripId),
  })

  const destinationsQuery = useQuery({
    queryKey: queryKeys.destinations,
    queryFn: listSupportedDestinations,
    staleTime: 10 * 60_000,
  })

  useEffect(() => {
    if (tripQuery.data && !destination) {
      setDestination(tripQuery.data.destination)
    }
  }, [tripQuery.data, destination])

  const searchQuery = useQuery({
    queryKey: queryKeys.places(searchParams ?? {}),
    queryFn: ({ signal }) => searchPlaces(searchParams as PlaceSearchParams, signal),
    enabled: searchParams !== null,
    retry: false,
    staleTime: 5 * 60_000,
  })

  useEffect(() => {
    if (!searchQuery.isFetching) {
      setElapsedSeconds(0)
      return
    }

    const startedAt = Date.now()

    const timer = window.setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000))
    }, 1000)

    return () => {
      window.clearInterval(timer)
    }
  }, [searchQuery.isFetching])

  const toggleCategory = (category: PlaceCategory) => {
    setSelectedCategories((current) =>
      current.includes(category)
        ? current.filter((entry) => entry !== category)
        : [...current, category],
    )
  }

  const handleSearch = () => {
    setFormError(null)

    const trimmedDestination = destination.trim()

    if (!trimmedDestination) {
      setFormError("Enter a destination, or choose one from the curated list.")
      return
    }

    const numericRadius = Number(radius)

    if (
      !Number.isFinite(numericRadius) ||
      numericRadius < 0.1 ||
      numericRadius > 25
    ) {
      setFormError("Radius must be between 0.1 and 25 km.")
      return
    }

    const numericLimit = Number(limit)

    if (!Number.isInteger(numericLimit) || numericLimit < 1 || numericLimit > 20) {
      setFormError("Results must be between 1 and 20.")
      return
    }

    setSearchParams({
      destination: trimmedDestination,
      radius_km: numericRadius,
      limit: numericLimit,
      categories:
        selectedCategories.length > 0 ? selectedCategories : undefined,
    })
  }

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
  const places = searchQuery.data ?? []

  return (
    <div className="space-y-8">
      <PageHeader
        backTo={`/trips/${trip.id}`}
        backLabel={trip.title}
        title="Search places"
        description="Verified points of interest from OpenStreetMap. A search can take 20–40 seconds because the provider is shared infrastructure."
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <SlidersHorizontal className="size-4" />
            Search area
          </CardTitle>
          <CardDescription>
            Only the curated Indian cities below can be searched by name.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-2 sm:col-span-2">
              <Label htmlFor="place-destination">Destination</Label>
              <div className="flex gap-2">
                <Input
                  id="place-destination"
                  value={destination}
                  onChange={(event) => setDestination(event.target.value)}
                  placeholder="Jaipur"
                />
                <Popover
                  open={destinationPickerOpen}
                  onOpenChange={setDestinationPickerOpen}
                >
                  <PopoverTrigger asChild>
                    <Button variant="outline">Browse</Button>
                  </PopoverTrigger>
                  <PopoverContent align="end" className="w-72 p-2">
                    {destinationsQuery.isPending ? (
                      <LoadingState className="py-4" />
                    ) : destinationsQuery.isError ? (
                      <p className="p-2 text-sm text-destructive">
                        {getErrorMessage(destinationsQuery.error)}
                      </p>
                    ) : (
                      <div className="max-h-72 space-y-1 overflow-y-auto">
                        {destinationsQuery.data.map((entry) => (
                          <button
                            key={`${entry.name}-${entry.state}`}
                            type="button"
                            className="flex w-full flex-col rounded-md px-2 py-1.5 text-left text-sm hover:bg-muted"
                            onClick={() => {
                              setDestination(entry.name)
                              setDestinationPickerOpen(false)
                            }}
                          >
                            <span className="font-medium">{entry.name}</span>
                            <span className="text-xs text-muted-foreground">
                              {entry.state}
                            </span>
                          </button>
                        ))}
                      </div>
                    )}
                  </PopoverContent>
                </Popover>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="place-radius">Radius (km)</Label>
              <Input
                id="place-radius"
                type="number"
                min="0.1"
                max="25"
                step="0.5"
                value={radius}
                onChange={(event) => setRadius(event.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="place-limit">Results</Label>
              <Input
                id="place-limit"
                type="number"
                min="1"
                max="20"
                step="1"
                value={limit}
                onChange={(event) => setLimit(event.target.value)}
              />
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <Label>Categories</Label>
              {selectedCategories.length > 0 ? (
                <button
                  type="button"
                  className="text-xs text-muted-foreground underline-offset-4 hover:underline"
                  onClick={() => setSelectedCategories([])}
                >
                  All categories
                </button>
              ) : null}
            </div>
            <div className="flex flex-wrap gap-2">
              {CATEGORIES.map((category) => {
                const selected = selectedCategories.includes(category.value)

                return (
                  <button
                    key={category.value}
                    type="button"
                    aria-pressed={selected}
                    onClick={() => toggleCategory(category.value)}
                    className={cn(
                      "rounded-full border px-3 py-1 text-xs transition-colors",
                      selected
                        ? "border-primary bg-primary text-primary-foreground"
                        : "bg-background text-muted-foreground hover:border-foreground/30 hover:text-foreground",
                    )}
                  >
                    {category.label}
                  </button>
                )
              })}
            </div>
            <p className="text-xs text-muted-foreground">
              Leave everything unselected to search all categories.
            </p>
          </div>

          {formError ? (
            <p className="rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              {formError}
            </p>
          ) : null}

          <Button
            onClick={handleSearch}
            disabled={searchQuery.isFetching}
          >
            <Search className="size-4" />
            {searchQuery.isFetching ? "Searching…" : "Search places"}
          </Button>
        </CardContent>
      </Card>

      <div className="flex items-start gap-3 rounded-xl border bg-muted/40 px-4 py-3 text-sm">
        <Info className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
        <p className="text-muted-foreground">
          The first search for an area is the slowest. Results are cached by
          the backend, so repeating the same search should be faster.
        </p>
      </div>

      {searchQuery.isFetching ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-14 text-center">
            <Loader2 className="size-7 animate-spin text-muted-foreground" />
            <div className="space-y-1">
              <p className="font-medium">Searching OpenStreetMap…</p>
              <p className="text-sm text-muted-foreground">
                Elapsed: {elapsedSeconds}s. This usually takes 20–40 seconds.
              </p>
            </div>
            <p className="max-w-md text-xs text-muted-foreground">
              You can keep this tab open; the request is still running. A
              timeout after 60 seconds usually means the shared provider is
              busy.
            </p>
          </CardContent>
        </Card>
      ) : searchQuery.isError ? (
        <ErrorState
          title="Place search failed"
          message={getErrorMessage(searchQuery.error)}
          onRetry={() => {
            void searchQuery.refetch()
          }}
        />
      ) : searchParams && places.length === 0 ? (
        <EmptyState
          icon={<Compass className="size-6" />}
          title="No places found"
          description="Try a wider radius, a different category set, or one of the curated destinations."
        />
      ) : searchParams ? (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-medium">
              {places.length} {places.length === 1 ? "place" : "places"} near{" "}
              {searchParams.destination}
            </h2>
            <span className="text-xs text-muted-foreground">
              within {searchParams.radius_km} km
            </span>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {places.map((place) => (
              <PlaceCard key={`${place.source}-${place.source_id}`} place={place} />
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}
