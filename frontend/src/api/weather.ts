import { api } from "@/api/client"
import type { ApiEnvelope, TripWeather } from "@/api/types"
import { unwrap } from "@/lib/envelope"

/**
 * The forecast covers a fixed provider window and is cached by the backend,
 * so it is usually fast. A remote provider can still be slow, and the request
 * is bounded so the page does not hang indefinitely.
 */
const WEATHER_TIMEOUT = 20_000

export async function getTripWeather(
  tripId: string,
  signal?: AbortSignal,
): Promise<TripWeather> {
  const response = await api.get<ApiEnvelope<TripWeather>>(
    `/api/v1/trips/${tripId}/weather/`,
    {
      timeout: WEATHER_TIMEOUT,
      signal,
    },
  )

  return unwrap(response.data)
}
