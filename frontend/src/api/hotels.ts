import { api } from "@/api/client"
import type { ApiEnvelope, TripHotels } from "@/api/types"
import { unwrap } from "@/lib/envelope"

/** Overpass is shared infrastructure; a hotel search can take 20–40 seconds. */
const HOTEL_SEARCH_TIMEOUT = 60_000

export async function getTripHotels(
  tripId: string,
  signal?: AbortSignal,
): Promise<TripHotels> {
  const response = await api.get<ApiEnvelope<TripHotels>>(
    `/api/v1/trips/${tripId}/hotels/`,
    {
      timeout: HOTEL_SEARCH_TIMEOUT,
      signal,
    },
  )

  return unwrap(response.data)
}
