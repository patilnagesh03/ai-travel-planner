import { LogOut, Plane, Plus, UserRound } from "lucide-react"
import { Suspense } from "react"
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom"

import { useAuth } from "@/auth/auth-context"
import { LoadingState } from "@/components/shared/loading-state"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { NotificationBell } from "@/features/notifications/notification-bell"
import { initials } from "@/lib/format"
import { cn } from "@/lib/utils"

export function AppLayout() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()

  const handleSignOut = async () => {
    await signOut()
    navigate("/signin", { replace: true })
  }

  return (
    <div className="flex min-h-svh flex-col bg-muted/30">
      <header className="sticky top-0 z-40 border-b bg-background/90 backdrop-blur">
        <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between gap-4 px-4">
          <Link to="/trips" className="flex items-center gap-2.5">
            <span className="grid size-9 place-items-center rounded-xl bg-primary text-primary-foreground">
              <Plane className="size-4" />
            </span>
            <span className="flex flex-col leading-none">
              <span className="text-sm font-semibold tracking-tight">
                AI Travel Planner
              </span>
              <span className="mt-1 hidden text-[11px] text-muted-foreground sm:block">
                India-first itineraries
              </span>
            </span>
          </Link>

          <nav className="flex items-center gap-1">
            <NavLink
              to="/trips"
              className={({ isActive }) =>
                cn(
                  "rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
                  isActive && "bg-muted text-foreground",
                )
              }
            >
              Trips
            </NavLink>

            <Button asChild size="sm" className="ml-1 hidden sm:inline-flex">
              <Link to="/trips?new=1">
                <Plus className="size-4" />
                New trip
              </Link>
            </Button>

            {user ? <NotificationBell /> : null}

            {user ? (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button
                    type="button"
                    className="ml-1 grid size-9 place-items-center rounded-full border bg-background text-xs font-semibold transition-colors hover:bg-muted"
                    aria-label="Account menu"
                  >
                    {initials(user.first_name, user.last_name)}
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuLabel className="space-y-0.5">
                    <span className="block truncate text-sm font-medium">
                      {user.full_name || `${user.first_name} ${user.last_name}`}
                    </span>
                    <span className="block truncate text-xs font-normal text-muted-foreground">
                      {user.email}
                    </span>
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onSelect={() => navigate("/profile")}>
                    <UserRound className="size-4" />
                    Profile
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onSelect={() => {
                      void handleSignOut()
                    }}
                  >
                    <LogOut className="size-4" />
                    Sign out
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            ) : null}
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
        {/* Route chunks are fetched on navigation; the header and footer stay
            interactive while a page loads. */}
        <Suspense fallback={<LoadingState label="Loading page…" className="py-24" />}>
          <Outlet />
        </Suspense>
      </main>

      <footer className="border-t bg-background/60">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-1 px-4 py-5 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <span>AI Travel Planner · plan with real places, not invented ones.</span>
          <span>Built for Indian destinations.</span>
        </div>
      </footer>
    </div>
  )
}
