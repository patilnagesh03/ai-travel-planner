import type { ApiEnvelope } from "@/api/types"

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

export function isEnvelope<T>(value: unknown): value is ApiEnvelope<T> {
  return (
    isRecord(value) &&
    typeof value.success === "boolean" &&
    "data" in value
  )
}

/**
 * The API is inconsistent: auth/trips/preferences/places/AI wrap their payload
 * in {success, message, data}, while the itinerary PATCH and all itinerary-item
 * endpoints return the raw object or array. Normalise both here.
 */
export function unwrap<T>(value: T | ApiEnvelope<T>): T {
  return isEnvelope<T>(value) ? value.data : value
}
