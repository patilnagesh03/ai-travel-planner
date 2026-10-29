import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Loader2 } from "lucide-react"
import { useEffect, useState } from "react"
import { Controller, useForm } from "react-hook-form"
import { toast } from "sonner"
import { z } from "zod"

import {
  createItineraryItem,
  updateItineraryItem,
} from "@/api/itinerary"
import type {
  ActivityType,
  ItineraryItem,
  ItineraryItemPayload,
  Trip,
} from "@/api/types"
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { getErrorMessage } from "@/lib/api-error"
import { queryKeys } from "@/lib/query-keys"

export const ACTIVITY_TYPES: { value: ActivityType; label: string }[] = [
  { value: "attraction", label: "Attraction" },
  { value: "meal", label: "Meal" },
  { value: "activity", label: "Activity" },
  { value: "transport", label: "Transport" },
  { value: "accommodation", label: "Accommodation" },
  { value: "free_time", label: "Free time" },
  { value: "other", label: "Other" },
]

const itemSchema = z
  .object({
    date: z.string().min(1, "Pick a date."),
    title: z.string().trim().min(1, "Give the activity a title."),
    start_time: z.string().optional(),
    end_time: z.string().optional(),
    description: z.string().optional(),
    activity_type: z.enum([
      "meal",
      "attraction",
      "activity",
      "transport",
      "accommodation",
      "free_time",
      "other",
    ]),
    location_name: z.string().optional(),
    location_address: z.string().optional(),
    latitude: z
      .string()
      .optional()
      .refine(
        (value) => !value || (Number(value) >= -90 && Number(value) <= 90),
        "Latitude must be between -90 and 90.",
      ),
    longitude: z
      .string()
      .optional()
      .refine(
        (value) => !value || (Number(value) >= -180 && Number(value) <= 180),
        "Longitude must be between -180 and 180.",
      ),
    order: z
      .string()
      .min(1, "Enter an order.")
      .refine(
        (value) => /^\d+$/.test(value) && Number(value) >= 1,
        "Order must be at least 1.",
      ),
  })
  .refine(
    (values) =>
      !values.start_time ||
      !values.end_time ||
      values.end_time >= values.start_time,
    {
      path: ["end_time"],
      message: "End time must be on or after the start time.",
    },
  )

type ItemFormValues = z.infer<typeof itemSchema>

function timeInputValue(value: string | null): string {
  return value ? value.slice(0, 5) : ""
}

function nextOrderFor(
  items: ItineraryItem[],
  date: string,
  excludeId?: string,
): number {
  const orders = items
    .filter((item) => item.date === date && item.id !== excludeId)
    .map((item) => item.order)

  return Math.max(0, ...orders) + 1
}

function formValues(
  item: ItineraryItem | undefined,
  defaultDate: string,
  items: ItineraryItem[],
): ItemFormValues {
  if (item) {
    return {
      date: item.date,
      title: item.title,
      start_time: timeInputValue(item.start_time),
      end_time: timeInputValue(item.end_time),
      description: item.description ?? "",
      activity_type: item.activity_type,
      location_name: item.location_name ?? "",
      location_address: item.location_address ?? "",
      latitude: item.latitude ?? "",
      longitude: item.longitude ?? "",
      order: String(item.order),
    }
  }

  return {
    date: defaultDate,
    title: "",
    start_time: "",
    end_time: "",
    description: "",
    activity_type: "other",
    location_name: "",
    location_address: "",
    latitude: "",
    longitude: "",
    order: String(nextOrderFor(items, defaultDate)),
  }
}

function nullable(value: string | undefined): string | null {
  const trimmed = value?.trim() ?? ""

  return trimmed ? trimmed : null
}

export function ItineraryItemDialog({
  open,
  onOpenChange,
  itineraryId,
  trip,
  items,
  item,
  defaultDate,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  itineraryId: string
  trip: Trip
  items: ItineraryItem[]
  item?: ItineraryItem
  defaultDate?: string
}) {
  const queryClient = useQueryClient()
  const [formError, setFormError] = useState<string | null>(null)

  const initialDate = item?.date ?? defaultDate ?? trip.start_date

  const {
    control,
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm<ItemFormValues>({
    resolver: zodResolver(itemSchema),
    defaultValues: formValues(item, initialDate, items),
  })

  useEffect(() => {
    if (open) {
      reset(formValues(item, initialDate, items))
      setFormError(null)
    }
  }, [open, item, initialDate, items, reset])

  const selectedDate = watch("date")

  // Keep the order unique per day. When an existing item keeps its own date,
  // leave its order untouched so editing does not silently reorder it.
  useEffect(() => {
    if (!open || !selectedDate) {
      return
    }

    if (item && selectedDate === item.date) {
      return
    }

    setValue("order", String(nextOrderFor(items, selectedDate, item?.id)))
  }, [open, selectedDate, items, item, setValue])

  const mutation = useMutation({
    mutationFn: (values: ItemFormValues) => {
      const payload: ItineraryItemPayload = {
        date: values.date,
        title: values.title.trim(),
        start_time: nullable(values.start_time),
        end_time: nullable(values.end_time),
        description: nullable(values.description),
        activity_type: values.activity_type,
        location_name: nullable(values.location_name),
        location_address: nullable(values.location_address),
        latitude: nullable(values.latitude),
        longitude: nullable(values.longitude),
        order: Number(values.order),
      }

      return item
        ? updateItineraryItem(itineraryId, item.id, payload)
        : createItineraryItem(itineraryId, payload)
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.itineraryItems(itineraryId),
      })
      toast.success(item ? "Activity updated." : "Activity added.")
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
      <DialogContent className="max-h-[90svh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{item ? "Edit activity" : "Add activity"}</DialogTitle>
          <DialogDescription>
            Times and order are within a single day. The backend keeps order
            unique per day.
          </DialogDescription>
        </DialogHeader>

        <form
          className="space-y-5"
          onSubmit={handleSubmit((values) => mutation.mutate(values))}
          noValidate
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="item-date">Date</Label>
              <Input
                id="item-date"
                type="date"
                min={trip.start_date}
                max={trip.end_date}
                aria-invalid={!!errors.date}
                {...register("date")}
              />
              {errors.date ? (
                <p className="text-sm text-destructive">{errors.date.message}</p>
              ) : null}
            </div>

            <div className="space-y-2">
              <Label htmlFor="item-type">Type</Label>
              <Controller
                control={control}
                name="activity_type"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger id="item-type" className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {ACTIVITY_TYPES.map((type) => (
                        <SelectItem key={type.value} value={type.value}>
                          {type.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="item-title">Title</Label>
            <Input
              id="item-title"
              placeholder="Amber Fort at opening time"
              aria-invalid={!!errors.title}
              {...register("title")}
            />
            {errors.title ? (
              <p className="text-sm text-destructive">{errors.title.message}</p>
            ) : null}
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="item-start-time">Start time</Label>
              <Input
                id="item-start-time"
                type="time"
                {...register("start_time")}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="item-end-time">End time</Label>
              <Input id="item-end-time" type="time" {...register("end_time")} />
              {errors.end_time ? (
                <p className="text-sm text-destructive">
                  {errors.end_time.message}
                </p>
              ) : null}
            </div>

            <div className="space-y-2">
              <Label htmlFor="item-order">Order</Label>
              <Input
                id="item-order"
                type="number"
                min="1"
                step="1"
                aria-invalid={!!errors.order}
                {...register("order")}
              />
              {errors.order ? (
                <p className="text-sm text-destructive">
                  {errors.order.message}
                </p>
              ) : null}
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="item-description">Notes</Label>
            <Textarea
              id="item-description"
              rows={3}
              placeholder="What to see, tickets, timing notes…"
              {...register("description")}
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="item-location">Place name</Label>
              <Input
                id="item-location"
                placeholder="Amber Fort"
                {...register("location_name")}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="item-address">Address</Label>
              <Input
                id="item-address"
                placeholder="Devisinghpura, Amer"
                {...register("location_address")}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="item-latitude">Latitude</Label>
              <Input
                id="item-latitude"
                inputMode="decimal"
                placeholder="26.9855"
                aria-invalid={!!errors.latitude}
                {...register("latitude")}
              />
              {errors.latitude ? (
                <p className="text-sm text-destructive">
                  {errors.latitude.message}
                </p>
              ) : null}
            </div>

            <div className="space-y-2">
              <Label htmlFor="item-longitude">Longitude</Label>
              <Input
                id="item-longitude"
                inputMode="decimal"
                placeholder="75.8513"
                aria-invalid={!!errors.longitude}
                {...register("longitude")}
              />
              {errors.longitude ? (
                <p className="text-sm text-destructive">
                  {errors.longitude.message}
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
              ) : item ? (
                "Save activity"
              ) : (
                "Add activity"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
