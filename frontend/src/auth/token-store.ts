/**
 * Token storage policy:
 * - access token: in memory only (never touches disk)
 * - refresh token: localStorage, so a reload can restore the session
 *
 * The refresh token is rotated by the backend on every refresh, so callers
 * must always store the newest one.
 */

const REFRESH_TOKEN_KEY = "travel-planner.refresh-token"

let accessToken: string | null = null

export function getAccessToken(): string | null {
  return accessToken
}

export function setAccessToken(token: string | null): void {
  accessToken = token
}

export function getRefreshToken(): string | null {
  try {
    return window.localStorage.getItem(REFRESH_TOKEN_KEY)
  } catch {
    return null
  }
}

export function setRefreshToken(token: string | null): void {
  try {
    if (token) {
      window.localStorage.setItem(REFRESH_TOKEN_KEY, token)
    } else {
      window.localStorage.removeItem(REFRESH_TOKEN_KEY)
    }
  } catch {
    // Storage can be unavailable (private mode, quota). The session then
    // simply does not survive a reload, which is an acceptable degradation.
  }
}

export function clearTokens(): void {
  accessToken = null
  setRefreshToken(null)
}
