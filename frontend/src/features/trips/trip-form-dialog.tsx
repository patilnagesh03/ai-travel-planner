import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { addDays, format } from "date-fns"
import { Loader2 } from "lucide-react"
import { useEffect, useState } from "react"
import { useForm } from "react-hook-form"
import { toast } from "sonner"
import { z } from "zod"

import { createTrip, updateTrip } from "@/api/trips"
import type { Trip } from "@/api/types"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { getErrorMessage } from "@/lib/api-error"
import { queryKeys } from "@/lib/query-keys"

const tripSchema = z
  .object({
    title: z.string().trim().min(1, "Give the trip a title."),
    destination: z.string().trim().min(1, "Where are you going?"),
    origin: z
      .string()
      .trim()
      .max(255, "Use 255 characters or fewer."),
    start_date: z.string().min(1, "Pick a start date."),
    end_date: z.string().min(1, "Pick an end date."),
    budget: z
      .string()
      .min(1, "Enter a budget.")
      .refine(
        (value) => Number.isFinite(Number(value)) && Number(value) > 0,
        "Budget must be greater than zero.",
      ),
    currency: z
      .string()
      .trim()
      .regex(/^[A-Za-z]{3}$/, "Use a 3-letter currency code."),
    travelers: z
      .string()
      .min(1, "Enter the number of travellers.")
      .refine(
        (value) => /^\d+$/.test(value) && Number(value) >= 1,
        "There must be at least one traveller.",
      ),
  })
  .refine((values) => values.end_date >= values.start_date, {
    path: ["end_date"],
    message: "End date must be on or after the start date.",
  })

type TripFormValues = z.infer<typeof tripSchema>

function defaultValues(trip?: Trip): TripFormValues {
  if (trip) {
    return {
      title: trip.title,
      destination: trip.destination,
      origin: trip.origin,
      start_date: trip.start_date,
      end_date: trip.end_date,
      budget: trip.budget,
      currency: trip.currency,
      travelers: String(trip.travelers),
    }
  }

  const today = new Date()

  return {
    title: "",
    destination: "",
    origin: "",
    start_date: format(today, "yyyy-MM-dd"),
    end_date: format(addDays(today, 7), "yyyy-MM-dd"),
    budget: "",
    currency: "INR",
    travelers: "1",
  }
}

export function TripFormDialog({
  open,
  onOpenChange,
  trip,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  trip?: Trip
}) {
  const queryClient = useQueryClient()
  const [formError, setFormError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<TripFormValues>({
    resolver: zodResolver(tripSchema),
    defaultValues: defaultValues(trip),
  })

  useEffect(() => {
    if (open) {
      reset(defaultValues(trip))
      setFormError(null)
    }
  }, [open, trip, reset])

  const mutation = useMutation({
    mutationFn: (values: TripFormValues) => {
      const payload = {
        title: values.title.trim(),
        destination: values.destination.trim(),
        origin: values.origin.trim(),
        start_date: values.start_date,
        end_date: values.end_date,
        budget: values.budget,
        currency: values.currency.toUpperCase(),
        travelers: Number(values.travelers),
      }

      return trip ? updateTrip(trip.id, payload) : createTrip(payload)
    },
    onSuccess: (savedTrip) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.trips })
      queryClient.setQueryData(queryKeys.trip(savedTrip.id), savedTrip)
      toast.success(trip ? "Trip updated." : "Trip created.")
      onOpenChange(false)
    },
    onError: (error) => {
      setFormError(getErrorMessage(error))
    },
  })

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!mutation.isPending) {
          onOpenChange(nextOpen)
        }
      }}
    >
      <DialogContent className="max-h-[90svh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{trip ? "Edit trip" : "Create a trip"}</DialogTitle>
          <DialogDescription>
            {trip
              ? "Update the details of this trip."
              : "Start with the basics. You can add preferences and an itinerary next."}
          </DialogDescription>
        </DialogHeader>

        <form
          className="space-y-4"
          onSubmit={handleSubmit((values) => mutation.mutate(values))}
          noValidate
        >
          <div className="space-y-2">
            <Label htmlFor="trip-title">Title</Label>
            <Input
              id="trip-title"
              placeholder="Rajasthan in October"
              aria-invalid={!!errors.title}
              {...register("title")}
            />
            {errors.title ? (
              <p className="text-sm text-destructive">{errors.title.message}</p>
            ) : null}
          </div>

          <div className="space-y-2">
            <Label htmlFor="trip-destination">Destination</Label>
            <Input
              id="trip-destination"
              placeholder="Jaipur"
              aria-invalid={!!errors.destination}
              {...register("destination")}
            />
            {errors.destination ? (
              <p className="text-sm text-destructive">
                {errors.destination.message}
              </p>
            ) : null}
            <p className="text-xs text-muted-foreground">
              Use a supported Indian city. The place search matches this name.
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="trip-origin">Departure city (optional)</Label>
            <Input
              id="trip-origin"
              placeholder="Delhi"
              aria-invalid={!!errors.origin}
              {...register("origin")}
            />
            {errors.origin ? (
              <p className="text-sm text-destructive">{errors.origin.message}</p>
            ) : null}
            <p className="text-xs text-muted-foreground">
              Used to build flight search links. Leave it blank if you only
              need hotels and places.
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="trip-start-date">Start date</Label>
              <Input
                id="trip-start-date"
                type="date"
                aria-invalid={!!errors.start_date}
                {...register("start_date")}
              />
              {errors.start_date ? (
                <p className="text-sm text-destructive">
                  {errors.start_date.message}
                </p>
              ) : null}
            </div>

            <div className="space-y-2">
              <Label htmlFor="trip-end-date">End date</Label>
              <Input
                id="trip-end-date"
                type="date"
                aria-invalid={!!errors.end_date}
                {...register("end_date")}
              />
              {errors.end_date ? (
                <p className="text-sm text-destructive">
                  {errors.end_date.message}
                </p>
              ) : null}
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="trip-budget">Budget</Label>
              <Input
                id="trip-budget"
                type="number"
                min="0"
                step="0.01"
                placeholder="50000"
                aria-invalid={!!errors.budget}
                {...register("budget")}
              />
              {errors.budget ? (
                <p className="text-sm text-destructive">
                  {errors.budget.message}
                </p>
              ) : null}
            </div>

            <div className="space-y-2">
              <Label htmlFor="trip-currency">Currency</Label>
              <Input
                id="trip-currency"
                maxLength={3}
                placeholder="INR"
                aria-invalid={!!errors.currency}
                {...register("currency")}
              />
              {errors.currency ? (
                <p className="text-sm text-destructive">
                  {errors.currency.message}
                </p>
              ) : null}
            </div>

            <div className="space-y-2">
              <Label htmlFor="trip-travelers">Travellers</Label>
              <Input
                id="trip-travelers"
                type="number"
                min="1"
                step="1"
                aria-invalid={!!errors.travelers}
                {...register("travelers")}
              />
              {errors.travelers ? (
                <p className="text-sm text-destructive">
                  {errors.travelers.message}
                </p>
              ) : null}
            </div>
          </div>

          {formError ? (
            <p className="rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              {formError}
            </p>
          ) : null}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              disabled={mutation.isPending}
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  Saving…
                </>
              ) : trip ? (
                "Save changes"
              ) : (
                "Create trip"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
