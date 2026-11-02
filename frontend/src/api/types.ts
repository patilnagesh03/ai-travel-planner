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

export interface WeatherDay {
  date: string
  weather_code: number | null
  condition: string
  temperature_max: number | null
  temperature_min: number | null
  precipitation_probability: number | null
  wind_speed_max: number | null
  sunrise: string | null
  sunset: string | null
}

export interface WeatherDestination {
  name: string | null
  state: string | null
  latitude: number
  longitude: number
}

export interface WeatherUnits {
  temperature: string
  wind_speed: string
  precipitation_probability: string
}

export interface ForecastWindow {
  starts_on: string
  ends_on: string
}

export interface TripWeather {
  destination: WeatherDestination
  timezone: string | null
  units: WeatherUnits
  forecast_window: ForecastWindow
  trip_days: number
  covered_days: number
  days: WeatherDay[]
  note: string | null
  attribution: string
}

export interface CurrencyRates {
  base: string
  date: string | null
  rates: Record<string, number>
  attribution: string
}

export interface BoundingBox {
  south: number
  west: number
  north: number
  east: number
}

export interface ResolvedDestination {
  name: string
  state: string
  aliases: string[]
  latitude: number
  longitude: number
  bbox: BoundingBox
}

export type ExpenseCategory =
  | "transport"
  | "stay"
  | "food"
  | "activities"
  | "shopping"
  | "other"

export interface Expense {
  id: string
  trip: string
  title: string
  category: ExpenseCategory
  /** DRF serializes DecimalField values as strings. */
  amount: string
  spent_on: string
  notes: string | null
  created_at: string
  updated_at: string
}

export interface ExpensePayload {
  title: string
  category: ExpenseCategory
  amount: string
  spent_on: string
  notes?: string | null
}

export interface ExpenseCategoryTotal {
  category: ExpenseCategory
  label: string
  total: string
  count: number
}

export interface ExpenseSummary {
  currency: string
  budget: string
  total_spent: string
  remaining: string
  over_budget: boolean
  expense_count: number
  by_category: ExpenseCategoryTotal[]
}

/** The expense list carries its own summary so the two cannot disagree. */
export interface ExpenseList {
  expenses: Expense[]
  summary: ExpenseSummary
}

export type NotificationKind =
  | "budget_exceeded"
  | "trip_soon"
  | "trip_ended"

export interface Notification {
  id: string
  kind: NotificationKind
  title: string
  message: string
  trip: string | null
  trip_title: string | null
  is_read: boolean
  read_at: string | null
  created_at: string
}

export interface UnreadNotificationCount {
  unread: number
}

export interface ReadAllNotificationsResult {
  updated: number
}
