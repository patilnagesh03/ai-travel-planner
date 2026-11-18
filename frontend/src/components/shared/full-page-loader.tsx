import { Loader2 } from "lucide-react"

export function FullPageLoader({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="grid min-h-svh place-items-center bg-background">
      <div className="flex flex-col items-center gap-3 text-muted-foreground">
        <Loader2 className="size-6 animate-spin" />
        <p className="text-sm">{label}</p>
      </div>
    </div>
  )
}
