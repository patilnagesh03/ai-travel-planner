import { Compass } from "lucide-react"
import { Link } from "react-router-dom"

import { Button } from "@/components/ui/button"

export function NotFoundPage() {
  return (
    <div className="grid min-h-svh place-items-center bg-muted/30 px-4">
      <div className="flex max-w-md flex-col items-center gap-4 text-center">
        <span className="grid size-14 place-items-center rounded-full bg-muted text-muted-foreground">
          <Compass className="size-7" />
        </span>
        <div className="space-y-1">
          <h1 className="text-3xl font-semibold tracking-tight">Page not found</h1>
          <p className="text-sm text-muted-foreground">
            That page does not exist. Head back to your trips and keep planning.
          </p>
        </div>
        <Button asChild>
          <Link to="/trips">Back to trips</Link>
        </Button>
      </div>
    </div>
  )
}
