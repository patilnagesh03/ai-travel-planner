import { api } from "@/api/client"
import type {
  ApiEnvelope,
  Destination,
  Place,
  PlaceSearchParams,
  ResolvedDestination,
} from "@/api/types"
import { unwrap } from "@/lib/envelope"

/** Overpass is shared infrastructure; a search can take 20–40 seconds. */
const PLACE_SEARCH_TIMEOUT = 60_000

export async function searchPlaces(
  params: PlaceSearchParams,
  signal?: AbortSignal,
): Promise<Place[]> {
  const response = await api.get<ApiEnvelope<Place[]>>(
    "/api/v1/places/search/",
    {
      timeout: PLACE_SEARCH_TIMEOUT,
      signal,
      params: {
        destination: params.destination || undefined,
        latitude: params.latitude,
        longitude: params.longitude,
        radius_km: params.radius_km,
        categories:
          params.categories && params.categories.length > 0
            ? params.categories.join(",")
            : undefined,
        limit: params.limit,
      },
    },
  )

  return unwrap(response.data)
}

export async function listSupportedDestinations(): Promise<Destination[]> {
  const response = await api.get<ApiEnvelope<Destination[]>>(
    "/api/v1/places/destinations/",
  )

  return unwrap(response.data)
}

/**
 * Resolve a free-text destination to the backend's curated coordinates.
 *
 * The map uses this instead of keeping its own copy of the city list, so a
 * destination that works for place search also centres the map.
 */
export async function resolveDestination(
  destination: string,
  signal?: AbortSignal,
): Promise<ResolvedDestination> {
  const response = await api.get<ApiEnvelope<ResolvedDestination>>(
    "/api/v1/places/resolve/",
    {
      signal,
      params: { destination },
    },
  )

  return unwrap(response.data)
}
