import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: {
  icon?: ReactNode
  title: string
  description?: string
  action?: ReactNode
  className?: string
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center gap-4 rounded-xl border border-dashed px-6 py-14 text-center",
        className,
      )}
    >
      {icon ? (
        <span className="grid size-12 place-items-center rounded-full bg-muted text-muted-foreground">
          {icon}
        </span>
      ) : null}
      <div className="space-y-1">
        <h3 className="text-lg font-medium">{title}</h3>
        {description ? (
          <p className="mx-auto max-w-md text-sm text-muted-foreground">
            {description}
          </p>
        ) : null}
      </div>
      {action}
    </div>
  )
}
