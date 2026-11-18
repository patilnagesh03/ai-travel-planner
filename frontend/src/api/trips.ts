import { api } from "@/api/client"
import type { ApiEnvelope, Trip, TripPayload } from "@/api/types"
import { unwrap } from "@/lib/envelope"

export async function listTrips(): Promise<Trip[]> {
  const response = await api.get<ApiEnvelope<Trip[]>>("/api/v1/trips/")

  return unwrap(response.data)
}

export async function getTrip(tripId: string): Promise<Trip> {
  const response = await api.get<ApiEnvelope<Trip>>(
    `/api/v1/trips/${tripId}/`,
  )

  return unwrap(response.data)
}

export async function createTrip(payload: TripPayload): Promise<Trip> {
  const response = await api.post<ApiEnvelope<Trip>>(
    "/api/v1/trips/",
    payload,
  )

  return unwrap(response.data)
}

export async function updateTrip(
  tripId: string,
  payload: Partial<TripPayload>,
): Promise<Trip> {
  const response = await api.patch<ApiEnvelope<Trip>>(
    `/api/v1/trips/${tripId}/`,
    payload,
  )

  return unwrap(response.data)
}

export async function deleteTrip(tripId: string): Promise<void> {
  await api.delete(`/api/v1/trips/${tripId}/`)
}
