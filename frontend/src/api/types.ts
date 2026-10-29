/**
 * Types mirrored from the Django/DRF serializers.
 *
 * The backend has no OpenAPI schema, so these are hand-maintained. Keep them
 * in sync with backend serializers when the API changes.
 */

export interface ApiEnvelope<T> {
  success: boolean
  message: string
  data: T
}

export interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  full_name: string
  phone_number: string | null
  profile_picture: string | null
  country: string | null
  city: string | null
  date_of_birth: string | null
  is_verified: boolean
  created_at: string
  updated_at: string
}

export interface AuthUser {
  id: string
  email: string
  first_name: string
  last_name: string
}

export interface AuthTokens {
  access: string
  refresh: string
}

export interface SignInResponse {
  user: AuthUser
  tokens: AuthTokens
}

export interface SignUpPayload {
  email: string
  first_name: string
  last_name: string
  password: string
  confirm_password: string
  phone_number?: string
  country?: string
  city?: string
  date_of_birth?: string
}

export interface SignUpResponse {
  id: string
  email: string
  first_name: string
  last_name: string
}

export interface ProfilePayload {
  first_name?: string
  last_name?: string
  phone_number?: string | null
  country?: string | null
  city?: string | null
  date_of_birth?: string | null
}

export interface ChangePasswordPayload {
  current_password: string
  new_password: string
  confirm_password: string
}

export interface Trip {
  id: string
  title: string
  destination: string
  start_date: string
  end_date: string
  /** DRF serializes DecimalField values as strings. */
  budget: string
  currency: string
  travelers: number
  created_at: string
  updated_at: string
}

export interface TripPayload {
  title: string
  destination: string
  start_date: string
  end_date: string
  budget: string
  currency: string
  travelers: number
}

export type TravelStyle = "relaxed" | "balanced" | "adventurous"
export type AccommodationType = "budget" | "mid_range" | "luxury"
export type TravelPace = "slow" | "moderate" | "fast"

export interface Interest {
  id: string
  name: string
}

export interface TripPreference {
  id: string
  trip: string
  travel_style: TravelStyle
  accommodation: AccommodationType | null
  pace: TravelPace
  interests: Interest[]
  created_at: string
  updated_at: string
}

export interface TripPreferencePayload {
  travel_style: TravelStyle
  accommodation: AccommodationType | null
  pace: TravelPace
  interest_ids: string[]
}

export type ActivityType =
  | "meal"
  | "attraction"
  | "activity"
  | "transport"
  | "accommodation"
  | "free_time"
  | "other"

export interface Itinerary {
  id: string
  trip: string
  title: string
  description: string | null
  created_at: string
  updated_at: string
}

export interface ItineraryPayload {
  title: string
  description?: string | null
}

export interface ItineraryItem {
  id: string
  itinerary: string
  date: string
  start_time: string | null
  end_time: string | null
  title: string
  description: string | null
  location_name: string | null
  location_address: string | null
  latitude: string | null
  longitude: string | null
  activity_type: ActivityType
  order: number
  created_at: string
  updated_at: string
}

export interface ItineraryItemPayload {
  date: string
  start_time?: string | null
  end_time?: string | null
  title: string
  description?: string | null
  location_name?: string | null
  location_address?: string | null
  latitude?: string | null
  longitude?: string | null
  activity_type: ActivityType
  order: number
}

export type PlaceCategory =
  | "attraction"
  | "museum"
  | "viewpoint"
  | "monument"
  | "religious_site"
  | "park"
  | "restaurant"
  | "cafe"
  | "other"

export interface Place {
  source: string
  source_id: string
  name: string
  category: PlaceCategory
  latitude: number
  longitude: number
  address: string | null
  opening_hours: string | null
}

export interface Destination {
  name: string
  state: string
  aliases: string[]
  latitude: number
  longitude: number
}

export interface PlaceSearchParams {
  destination?: string
  latitude?: number
  longitude?: number
  radius_km?: number
  categories?: PlaceCategory[]
  limit?: number
}

export interface GeneratedPlace {
  source_id: string
  name: string
  latitude: number | null
  longitude: number | null
  address: string | null
}

export interface GeneratedItem {
  title: string
  description: string | null
  start_time: string | null
  end_time: string | null
  activity_type: ActivityType
  place: GeneratedPlace
}

export interface GeneratedDay {
  date: string
  items: GeneratedItem[]
}

export interface GeneratedPlan {
  title: string
  description: string | null
  days: GeneratedDay[]
}

export interface GenerationResult {
  itinerary_id: string | null
  persisted: boolean
  plan: GeneratedPlan
}

export interface GenerationPayload {
  dry_run?: boolean
  replace?: boolean
}

export interface AiStatus {
  provider: string
  model: string
  base_url: string
  available: boolean
}
