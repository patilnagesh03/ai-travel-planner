import { CalendarDays, Compass, Sparkles } from "lucide-react"
import type { ReactNode } from "react"
import { Link } from "react-router-dom"

export function AuthLayout({
  title,
  description,
  children,
  footer,
}: {
  title: string
  description: string
  children: ReactNode
  footer?: ReactNode
}) {
  return (
    <div className="grid min-h-svh bg-background lg:grid-cols-2">
      <div className="relative hidden overflow-hidden bg-primary p-10 text-primary-foreground lg:flex lg:flex-col lg:justify-between">
        <div
          aria-hidden
          className="pointer-events-none absolute -right-24 -top-24 size-96 rounded-full bg-primary-foreground/5 blur-3xl"
        />
        <Link to="/" className="flex items-center gap-2.5">
          <span className="grid size-9 place-items-center rounded-xl bg-primary-foreground/10">
            <Compass className="size-5" />
          </span>
          <span className="text-sm font-semibold tracking-tight">
            AI Travel Planner
          </span>
        </Link>

        <div className="relative max-w-md space-y-6">
          <h2 className="text-3xl font-semibold leading-tight tracking-tight">
            Real places. Sensible days. No invented addresses.
          </h2>
          <p className="text-sm leading-relaxed text-primary-foreground/70">
            Plan an Indian trip around verified points of interest, keep every
            day editable, and let a local AI model draft the first version.
          </p>
          <ul className="space-y-4 text-sm text-primary-foreground/80">
            <li className="flex items-start gap-3">
              <Sparkles className="mt-0.5 size-4 shrink-0" />
              <span>
                AI drafts are grounded in real OpenStreetMap places, never made
                up.
              </span>
            </li>
            <li className="flex items-start gap-3">
              <CalendarDays className="mt-0.5 size-4 shrink-0" />
              <span>
                Every generated day stays editable — times, order and notes are
                yours.
              </span>
            </li>
            <li className="flex items-start gap-3">
              <Compass className="mt-0.5 size-4 shrink-0" />
              <span>
                Curated, India-first destinations with a place search that
                respects your radius.
              </span>
            </li>
          </ul>
        </div>

        <p className="text-xs text-primary-foreground/50">
          Your trips stay private to your account.
        </p>
      </div>

      <div className="flex items-center justify-center px-4 py-10 sm:px-8">
        <div className="w-full max-w-md space-y-6">
          <div className="space-y-1.5 lg:hidden">
            <Link to="/" className="mb-6 flex items-center gap-2.5">
              <span className="grid size-9 place-items-center rounded-xl bg-primary text-primary-foreground">
                <Compass className="size-4" />
              </span>
              <span className="text-sm font-semibold tracking-tight">
                AI Travel Planner
              </span>
            </Link>
          </div>

          <div className="space-y-1.5">
            <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
            <p className="text-sm text-muted-foreground">{description}</p>
          </div>

          {children}

          {footer ? (
            <div className="text-sm text-muted-foreground">{footer}</div>
          ) : null}
        </div>
      </div>
    </div>
  )
}
