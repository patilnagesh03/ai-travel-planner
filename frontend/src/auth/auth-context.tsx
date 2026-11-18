import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react"

import { getProfile, logout as logoutRequest, signIn as signInRequest } from "@/api/auth"
import { refreshAccessToken, setUnauthorizedHandler } from "@/api/client"
import type { User } from "@/api/types"
import {
  clearTokens,
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
} from "@/auth/token-store"

export type AuthStatus = "loading" | "authenticated" | "anonymous"

interface SignInValues {
  email: string
  password: string
}

interface AuthContextValue {
  user: User | null
  status: AuthStatus
  signIn: (values: SignInValues) => Promise<void>
  signOut: () => Promise<void>
  updateUser: (user: User) => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [status, setStatus] = useState<AuthStatus>("loading")
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true

    setUnauthorizedHandler(() => {
      if (mountedRef.current) {
        setUser(null)
        setStatus("anonymous")
      }
    })

    return () => {
      mountedRef.current = false
      setUnauthorizedHandler(null)
    }
  }, [])

  useEffect(() => {
    let cancelled = false

    const bootstrap = async () => {
      if (!getRefreshToken()) {
        if (!cancelled) {
          setStatus("anonymous")
        }
        return
      }

      try {
        await refreshAccessToken()

        const profile = await getProfile()

        if (!cancelled) {
          setUser(profile)
          setStatus("authenticated")
        }
      } catch {
        clearTokens()

        if (!cancelled) {
          setUser(null)
          setStatus("anonymous")
        }
      }
    }

    void bootstrap()

    return () => {
      cancelled = true
    }
  }, [])

  const signIn = useCallback(async (values: SignInValues) => {
    const result = await signInRequest(values)

    setAccessToken(result.tokens.access)
    setRefreshToken(result.tokens.refresh)

    try {
      const profile = await getProfile()

      setUser(profile)
      setStatus("authenticated")
    } catch (error) {
      clearTokens()
      setUser(null)
      setStatus("anonymous")
      throw error
    }
  }, [])

  const signOut = useCallback(async () => {
    const refreshToken = getRefreshToken()

    try {
      if (refreshToken) {
        await logoutRequest(refreshToken)
      }
    } catch {
      // Signing out locally must succeed even if the server call fails.
    } finally {
      clearTokens()
      setUser(null)
      setStatus("anonymous")
    }
  }, [])

  const updateUser = useCallback((nextUser: User) => {
    setUser(nextUser)
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      status,
      signIn,
      signOut,
      updateUser,
    }),
    [user, status, signIn, signOut, updateUser],
  )

  return (
    <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)

  if (!context) {
    throw new Error("useAuth must be used inside an AuthProvider.")
  }

  return context
}
