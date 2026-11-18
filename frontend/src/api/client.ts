import axios, {
  type AxiosError,
  type InternalAxiosRequestConfig,
} from "axios"

import type { ApiEnvelope } from "@/api/types"
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
} from "@/auth/token-store"
import { unwrap } from "@/lib/envelope"

export const apiBaseUrl = (
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000"
).replace(/\/+$/, "")

export const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 30_000,
  headers: {
    Accept: "application/json",
  },
})

api.interceptors.request.use((config) => {
  const token = getAccessToken()

  if (token) {
    config.headers.set("Authorization", `Bearer ${token}`)
  }

  return config
})

type RetryableConfig = InternalAxiosRequestConfig & {
  _retry?: boolean
}

const AUTH_ENDPOINTS = [
  "/api/auth/signin/",
  "/api/auth/signup/",
  "/api/auth/refresh-token/",
]

function isAuthEndpoint(url: string | undefined): boolean {
  return (
    !!url && AUTH_ENDPOINTS.some((endpoint) => url.includes(endpoint))
  )
}

let unauthorizedHandler: (() => void) | null = null

export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler
}

function notifyUnauthorized(): void {
  clearTokens()
  unauthorizedHandler?.()
}

interface RefreshedTokens {
  access: string
  refresh?: string
}

async function requestNewAccessToken(): Promise<string> {
  const refreshToken = getRefreshToken()

  if (!refreshToken) {
    throw new Error("No refresh token is available.")
  }

  const response = await axios.post<ApiEnvelope<RefreshedTokens>>(
    `${apiBaseUrl}/api/auth/refresh-token/`,
    { refresh: refreshToken },
    {
      timeout: 30_000,
      headers: { "Content-Type": "application/json" },
    },
  )

  const tokens = unwrap(response.data)

  setAccessToken(tokens.access)

  // Rotation is enabled on the backend: the old refresh token is blacklisted
  // as soon as it is used, so the new one must be persisted immediately.
  if (tokens.refresh) {
    setRefreshToken(tokens.refresh)
  }

  return tokens.access
}

let refreshInFlight: Promise<string> | null = null

/**
 * Refresh the access token. Concurrent callers share one request, which is
 * essential because the backend blacklists the previous refresh token.
 */
export function refreshAccessToken(): Promise<string> {
  if (!refreshInFlight) {
    refreshInFlight = requestNewAccessToken().finally(() => {
      refreshInFlight = null
    })
  }

  return refreshInFlight
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as RetryableConfig | undefined
    const status = error.response?.status

    if (
      status !== 401 ||
      !config ||
      config._retry ||
      isAuthEndpoint(config.url)
    ) {
      return Promise.reject(error)
    }

    if (!getRefreshToken()) {
      notifyUnauthorized()
      return Promise.reject(error)
    }

    config._retry = true

    try {
      const accessToken = await refreshAccessToken()

      config.headers.set("Authorization", `Bearer ${accessToken}`)

      return api(config)
    } catch (refreshError) {
      notifyUnauthorized()
      return Promise.reject(refreshError)
    }
  },
)
