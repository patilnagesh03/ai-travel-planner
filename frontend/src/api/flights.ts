import { api } from "@/api/client"
import type { ApiEnvelope, TripFlightLinks } from "@/api/types"
import { unwrap } from "@/lib/envelope"

/** The endpoint only builds URLs, so it should answer immediately. */
const FLIGHT_LINKS_TIMEOUT = 10_000

export async function getTripFlightLinks(
  tripId: string,
  signal?: AbortSignal,
): Promise<TripFlightLinks> {
  const response = await api.get<ApiEnvelope<TripFlightLinks>>(
    `/api/v1/trips/${tripId}/flights/`,
    {
      timeout: FLIGHT_LINKS_TIMEOUT,
      signal,
    },
  )

  return unwrap(response.data)
}
