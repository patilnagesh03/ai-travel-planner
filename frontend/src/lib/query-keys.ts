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
  resolvedDestination: (destination: string) =>
    ["places", "resolve", destination] as const,
  weather: (tripId: string) => ["weather", tripId] as const,
  currencyRates: (base: string, symbols: string[]) =>
    ["currency", base, symbols] as const,
  expenses: (tripId: string) => ["expenses", tripId] as const,
  notifications: (unreadOnly: boolean) =>
    ["notifications", unreadOnly] as const,
  notificationUnreadCount: ["notifications", "unread-count"] as const,
  aiStatus: ["ai", "status"] as const,
}
