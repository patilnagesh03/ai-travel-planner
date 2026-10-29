import axios from "axios"

import { isRecord } from "@/lib/envelope"

function humaniseField(field: string): string {
  if (field === "non_field_errors" || field === "detail") {
    return ""
  }

  const words = field.replaceAll("_", " ").trim()

  return words.charAt(0).toUpperCase() + words.slice(1)
}

function describeFieldErrors(data: Record<string, unknown>): string | null {
  const parts: string[] = []

  for (const [field, value] of Object.entries(data)) {
    if (field === "success" || field === "message" || field === "data") {
      continue
    }

    const messages = Array.isArray(value)
      ? value.filter((entry): entry is string => typeof entry === "string")
      : typeof value === "string"
        ? [value]
        : []

    if (messages.length === 0) {
      continue
    }

    const label = humaniseField(field)

    parts.push(label ? `${label}: ${messages.join(" ")}` : messages.join(" "))
  }

  return parts.length > 0 ? parts.join(" ") : null
}

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data: unknown = error.response?.data

    if (typeof data === "string" && data.trim()) {
      return data
    }

    if (isRecord(data)) {
      if (typeof data.message === "string" && data.message.trim()) {
        return data.message
      }

      if (typeof data.detail === "string" && data.detail.trim()) {
        return data.detail
      }

      const fieldErrors = describeFieldErrors(data)

      if (fieldErrors) {
        return fieldErrors
      }
    }

    if (!error.response) {
      if (error.code === "ECONNABORTED" || error.code === "ETIMEDOUT") {
        return "The request took too long. The server may still be working — please try again."
      }

      return "Could not reach the server. Check that the Django backend is running."
    }

    if (error.response.status === 401) {
      return "Your session has expired. Please sign in again."
    }

    if (error.response.status === 403) {
      return "You do not have permission to do that."
    }

    if (error.response.status === 404) {
      return "That resource could not be found."
    }

    return `The request failed (HTTP ${error.response.status}).`
  }

  if (error instanceof Error) {
    return error.message
  }

  return "Something went wrong. Please try again."
}

export function getErrorStatus(error: unknown): number | null {
  return axios.isAxiosError(error) ? (error.response?.status ?? null) : null
}

export function isNotFound(error: unknown): boolean {
  return getErrorStatus(error) === 404
}

export function isConflict(error: unknown): boolean {
  return getErrorStatus(error) === 409
}
