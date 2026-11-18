import { api } from "@/api/client"
import type {
  ApiEnvelope,
  Interest,
  TripPreference,
  TripPreferencePayload,
} from "@/api/types"
import { unwrap } from "@/lib/envelope"

export async function listInterests(): Promise<Interest[]> {
  const response = await api.get<ApiEnvelope<Interest[]>>(
    "/api/v1/interests/",
  )

  return unwrap(response.data)
}

export async function getPreferences(
  tripId: string,
): Promise<TripPreference> {
  const response = await api.get<ApiEnvelope<TripPreference>>(
    `/api/v1/trips/${tripId}/preferences/`,
  )

  return unwrap(response.data)
}

export async function createPreferences(
  tripId: string,
  payload: TripPreferencePayload,
): Promise<TripPreference> {
  const response = await api.post<ApiEnvelope<TripPreference>>(
    `/api/v1/trips/${tripId}/preferences/`,
    payload,
  )

  return unwrap(response.data)
}

export async function updatePreferences(
  tripId: string,
  payload: Partial<TripPreferencePayload>,
): Promise<TripPreference> {
  const response = await api.patch<ApiEnvelope<TripPreference>>(
    `/api/v1/trips/${tripId}/preferences/`,
    payload,
  )

  return unwrap(response.data)
}

export async function deletePreferences(tripId: string): Promise<void> {
  await api.delete(`/api/v1/trips/${tripId}/preferences/`)
}
