import {
  ArrowRight,
  CalendarDays,
  MapPin,
  MoreHorizontal,
  Pencil,
  Trash2,
  Users,
  Wallet,
} from "lucide-react"
import { Link } from "react-router-dom"

import type { Trip } from "@/api/types"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  formatCurrency,
  formatDateRange,
  tripDayCount,
} from "@/lib/format"

export function TripCard({
  trip,
  onEdit,
  onDelete,
}: {
  trip: Trip
  onEdit: (trip: Trip) => void
  onDelete: (trip: Trip) => void
}) {
  const dayCount = tripDayCount(trip.start_date, trip.end_date)

  return (
    <Card className="group flex flex-col transition-shadow hover:shadow-md">
      <CardHeader className="gap-1.5">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <p className="flex items-center gap-1 text-xs font-medium text-muted-foreground">
              <MapPin className="size-3.5" />
              {trip.destination}
            </p>
            <CardTitle className="text-lg leading-snug">
              <Link
                to={`/trips/${trip.id}`}
                className="transition-colors hover:text-primary"
              >
                {trip.title}
              </Link>
            </CardTitle>
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label={`Actions for ${trip.title}`}
              >
                <MoreHorizontal className="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onSelect={() => onEdit(trip)}>
                <Pencil className="size-4" />
                Edit trip
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                variant="destructive"
                onSelect={() => onDelete(trip)}
              >
                <Trash2 className="size-4" />
                Delete trip
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>

      <CardContent className="flex-1 space-y-3">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <CalendarDays className="size-4 shrink-0" />
          <span>{formatDateRange(trip.start_date, trip.end_date)}</span>
          <span className="text-xs">· {dayCount} days</span>
        </div>

        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Users className="size-4 shrink-0" />
            <span>
              {trip.travelers} {trip.travelers === 1 ? "traveller" : "travellers"}
            </span>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground">
            <Wallet className="size-4 shrink-0" />
            <span className="truncate">
              {formatCurrency(trip.budget, trip.currency)}
            </span>
          </div>
        </div>
      </CardContent>

      <CardFooter className="justify-between border-t bg-muted/30">
        <span className="text-xs text-muted-foreground">
          {trip.currency} budget
        </span>
        <Button variant="ghost" size="sm" asChild>
          <Link to={`/trips/${trip.id}`}>
            Open trip
            <ArrowRight className="size-4" />
          </Link>
        </Button>
      </CardFooter>
    </Card>
  )
}
