import { api } from "@/api/client"
import type {
  ApiEnvelope,
  Itinerary,
  ItineraryItem,
  ItineraryItemPayload,
  ItineraryPayload,
} from "@/api/types"
import { unwrap } from "@/lib/envelope"

export async function getItinerary(tripId: string): Promise<Itinerary> {
  const response = await api.get<ApiEnvelope<Itinerary>>(
    `/api/v1/trips/${tripId}/itinerary/`,
  )

  return unwrap(response.data)
}

export async function createItinerary(
  tripId: string,
  payload: ItineraryPayload,
): Promise<Itinerary> {
  const response = await api.post<ApiEnvelope<Itinerary>>(
    `/api/v1/trips/${tripId}/itinerary/`,
    payload,
  )

  return unwrap(response.data)
}

/** This endpoint returns the raw itinerary object, not an envelope. */
export async function updateItinerary(
  tripId: string,
  payload: Partial<ItineraryPayload>,
): Promise<Itinerary> {
  const response = await api.patch<Itinerary>(
    `/api/v1/trips/${tripId}/itinerary/`,
    payload,
  )

  return unwrap(response.data)
}

export async function deleteItinerary(tripId: string): Promise<void> {
  await api.delete(`/api/v1/trips/${tripId}/itinerary/`)
}

/** The item endpoints return raw objects/arrays, not envelopes. */
export async function listItineraryItems(
  itineraryId: string,
): Promise<ItineraryItem[]> {
  const response = await api.get<ItineraryItem[]>(
    `/api/v1/itineraries/${itineraryId}/items/`,
  )

  return unwrap(response.data)
}

export async function createItineraryItem(
  itineraryId: string,
  payload: ItineraryItemPayload,
): Promise<ItineraryItem> {
  const response = await api.post<ItineraryItem>(
    `/api/v1/itineraries/${itineraryId}/items/`,
    payload,
  )

  return unwrap(response.data)
}

export async function updateItineraryItem(
  itineraryId: string,
  itemId: string,
  payload: Partial<ItineraryItemPayload>,
): Promise<ItineraryItem> {
  const response = await api.patch<ItineraryItem>(
    `/api/v1/itineraries/${itineraryId}/items/${itemId}/`,
    payload,
  )

  return unwrap(response.data)
}

export async function deleteItineraryItem(
  itineraryId: string,
  itemId: string,
): Promise<void> {
  await api.delete(`/api/v1/itineraries/${itineraryId}/items/${itemId}/`)
}
