import type { PlaceSearchParams } from "@/api/types"

export const queryKeys = {
  profile: ["profile"] as const,
  trips: ["trips"] as const,
  trip: (tripId: string) => ["trips", tripId] as const,
  interests: ["interests"] as const,
  preferences: (tripId: string) => ["preferences", tripId] as const,
  itinerary: (tripId: string) => ["itinerary", tripId] as const,
  itineraryItems: (itineraryId: string) =>
    ["itinerary", itineraryId, "items"] as const,
  places: (params: PlaceSearchParams) => ["places", params] as const,
  destinations: ["places", "destinations"] as const,
  aiStatus: ["ai", "status"] as const,
}
