import type { ReactNode } from "react"
import { Navigate, useLocation } from "react-router-dom"

import { useAuth } from "@/auth/auth-context"
import { FullPageLoader } from "@/components/shared/full-page-loader"

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { status } = useAuth()
  const location = useLocation()

  if (status === "loading") {
    return <FullPageLoader label="Restoring your session…" />
  }

  if (status === "anonymous") {
    return (
      <Navigate
        to="/signin"
        replace
        state={{ from: `${location.pathname}${location.search}` }}
      />
    )
  }

  return children
}

export function PublicOnlyRoute({ children }: { children: ReactNode }) {
  const { status } = useAuth()

  if (status === "loading") {
    return <FullPageLoader label="Checking your session…" />
  }

  if (status === "authenticated") {
    return <Navigate to="/trips" replace />
  }

  return children
}
