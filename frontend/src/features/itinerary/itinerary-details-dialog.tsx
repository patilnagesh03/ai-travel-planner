import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Loader2 } from "lucide-react"
import { useEffect, useState } from "react"
import { useForm } from "react-hook-form"
import { toast } from "sonner"
import { z } from "zod"

import {
  createItinerary,
  updateItinerary,
} from "@/api/itinerary"
import type { Itinerary, Trip } from "@/api/types"
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
import { Textarea } from "@/components/ui/textarea"
import { getErrorMessage } from "@/lib/api-error"
import { queryKeys } from "@/lib/query-keys"

const detailsSchema = z.object({
  title: z.string().trim().min(1, "Give the itinerary a title."),
  description: z.string().optional(),
})

type DetailsFormValues = z.infer<typeof detailsSchema>

export function ItineraryDetailsDialog({
  open,
  onOpenChange,
  trip,
  itinerary,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  trip: Trip
  itinerary?: Itinerary
}) {
  const queryClient = useQueryClient()
  const [formError, setFormError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<DetailsFormValues>({
    resolver: zodResolver(detailsSchema),
    defaultValues: {
      title: itinerary?.title ?? `${trip.destination} itinerary`,
      description: itinerary?.description ?? "",
    },
  })

  useEffect(() => {
    if (open) {
      reset({
        title: itinerary?.title ?? `${trip.destination} itinerary`,
        description: itinerary?.description ?? "",
      })
      setFormError(null)
    }
  }, [open, itinerary, trip.destination, reset])

  const mutation = useMutation({
    mutationFn: (values: DetailsFormValues) => {
      const payload = {
        title: values.title.trim(),
        description: values.description?.trim() || null,
      }

      return itinerary
        ? updateItinerary(trip.id, payload)
        : createItinerary(trip.id, payload)
    },
    onSuccess: (savedItinerary) => {
      queryClient.setQueryData(
        queryKeys.itinerary(trip.id),
        savedItinerary,
      )
      void queryClient.invalidateQueries({
        queryKey: queryKeys.itinerary(trip.id),
      })
      toast.success(itinerary ? "Itinerary updated." : "Itinerary created.")
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
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {itinerary ? "Edit itinerary details" : "Create an itinerary"}
          </DialogTitle>
          <DialogDescription>
            {itinerary
              ? "Rename the itinerary or change its description."
              : "Start with an empty itinerary and add activities yourself."}
          </DialogDescription>
        </DialogHeader>

        <form
          className="space-y-4"
          onSubmit={handleSubmit((values) => mutation.mutate(values))}
          noValidate
        >
          <div className="space-y-2">
            <Label htmlFor="itinerary-title">Title</Label>
            <Input
              id="itinerary-title"
              aria-invalid={!!errors.title}
              {...register("title")}
            />
            {errors.title ? (
              <p className="text-sm text-destructive">{errors.title.message}</p>
            ) : null}
          </div>

          <div className="space-y-2">
            <Label htmlFor="itinerary-description">Description</Label>
            <Textarea
              id="itinerary-description"
              rows={4}
              placeholder="A slow week around forts, food and old city walks."
              {...register("description")}
            />
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
              ) : itinerary ? (
                "Save changes"
              ) : (
                "Create itinerary"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
