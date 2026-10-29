import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Info, Loader2, Save, Settings2, Trash2 } from "lucide-react"
import { useEffect, useState } from "react"
import { Controller, useForm } from "react-hook-form"
import { useParams } from "react-router-dom"
import { toast } from "sonner"
import { z } from "zod"

import {
  createPreferences,
  deletePreferences,
  getPreferences,
  listInterests,
  updatePreferences,
} from "@/api/preferences"
import { getTrip } from "@/api/trips"
import type { TripPreference } from "@/api/types"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { ErrorState } from "@/components/shared/error-state"
import { LoadingState } from "@/components/shared/loading-state"
import { PageHeader } from "@/components/shared/page-header"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { getErrorMessage, isNotFound } from "@/lib/api-error"
import { queryKeys } from "@/lib/query-keys"
import { cn } from "@/lib/utils"

const preferenceSchema = z.object({
  travel_style: z.enum(["relaxed", "balanced", "adventurous"]),
  accommodation: z.enum(["budget", "mid_range", "luxury"]).nullable(),
  pace: z.enum(["slow", "moderate", "fast"]),
  interest_ids: z.array(z.string()),
})

type PreferenceFormValues = z.infer<typeof preferenceSchema>

function valuesFromPreferences(
  preferences: TripPreference | null,
): PreferenceFormValues {
  return {
    travel_style: preferences?.travel_style ?? "balanced",
    accommodation: preferences?.accommodation ?? null,
    pace: preferences?.pace ?? "moderate",
    interest_ids: preferences?.interests.map((interest) => interest.id) ?? [],
  }
}

export function PreferencesPage() {
  const { tripId = "" } = useParams()
  const queryClient = useQueryClient()
  const [formError, setFormError] = useState<string | null>(null)
  const [deleteOpen, setDeleteOpen] = useState(false)

  const tripQuery = useQuery({
    queryKey: queryKeys.trip(tripId),
    queryFn: () => getTrip(tripId),
    enabled: Boolean(tripId),
  })

  const preferencesQuery = useQuery({
    queryKey: queryKeys.preferences(tripId),
    queryFn: async () => {
      try {
        return await getPreferences(tripId)
      } catch (error) {
        if (isNotFound(error)) {
          return null
        }

        throw error
      }
    },
    enabled: Boolean(tripId),
  })

  const interestsQuery = useQuery({
    queryKey: queryKeys.interests,
    queryFn: listInterests,
    staleTime: 10 * 60_000,
  })

  const preferences = preferencesQuery.data ?? null

  const {
    control,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { isDirty },
  } = useForm<PreferenceFormValues>({
    resolver: zodResolver(preferenceSchema),
    defaultValues: valuesFromPreferences(preferences),
  })

  useEffect(() => {
    if (preferencesQuery.isSuccess) {
      reset(valuesFromPreferences(preferencesQuery.data ?? null))
    }
  }, [preferencesQuery.isSuccess, preferencesQuery.data, reset])

  const selectedInterestIds = watch("interest_ids")

  const toggleInterest = (interestId: string) => {
    const next = selectedInterestIds.includes(interestId)
      ? selectedInterestIds.filter((id) => id !== interestId)
      : [...selectedInterestIds, interestId]

    setValue("interest_ids", next, {
      shouldDirty: true,
      shouldValidate: true,
    })
  }

  const saveMutation = useMutation({
    mutationFn: (values: PreferenceFormValues) =>
      preferences
        ? updatePreferences(tripId, values)
        : createPreferences(tripId, values),
    onSuccess: (savedPreferences) => {
      queryClient.setQueryData(
        queryKeys.preferences(tripId),
        savedPreferences,
      )
      void queryClient.invalidateQueries({
        queryKey: queryKeys.preferences(tripId),
      })
      reset(valuesFromPreferences(savedPreferences))
      setFormError(null)
      toast.success(
        preferences ? "Preferences updated." : "Preferences saved.",
      )
    },
    onError: (error) => {
      setFormError(getErrorMessage(error))
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => deletePreferences(tripId),
    onSuccess: () => {
      queryClient.setQueryData(queryKeys.preferences(tripId), null)
      reset(valuesFromPreferences(null))
      setDeleteOpen(false)
      toast.success("Preferences cleared.")
    },
    onError: (error) => {
      toast.error(getErrorMessage(error))
    },
  })

  if (tripQuery.isPending || preferencesQuery.isPending) {
    return <LoadingState label="Loading preferences…" />
  }

  if (tripQuery.isError) {
    return (
      <ErrorState
        title="Trip unavailable"
        message={getErrorMessage(tripQuery.error)}
        onRetry={() => {
          void tripQuery.refetch()
        }}
      />
    )
  }

  if (preferencesQuery.isError) {
    return (
      <ErrorState
        title="Preferences unavailable"
        message={getErrorMessage(preferencesQuery.error)}
        onRetry={() => {
          void preferencesQuery.refetch()
        }}
      />
    )
  }

  const trip = tripQuery.data

  return (
    <div className="space-y-8">
      <PageHeader
        backTo={`/trips/${trip.id}`}
        backLabel={trip.title}
        title="Trip preferences"
        description="These shape the AI draft: pacing, comfort level and what you actually enjoy."
        actions={
          preferences ? (
            <Button
              variant="outline"
              onClick={() => setDeleteOpen(true)}
              disabled={deleteMutation.isPending}
            >
              <Trash2 className="size-4" />
              Clear preferences
            </Button>
          ) : undefined
        }
      />

      {!preferences ? (
        <div className="flex items-start gap-3 rounded-xl border bg-muted/40 px-4 py-3 text-sm">
          <Info className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
          <p className="text-muted-foreground">
            No preferences yet. The planner will assume a balanced pace and
            moderate comfort until you save some.
          </p>
        </div>
      ) : null}

      <form
        onSubmit={handleSubmit((values) => saveMutation.mutate(values))}
        className="space-y-6"
      >
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Settings2 className="size-4" />
              Travel style
            </CardTitle>
            <CardDescription>
              How packed should the days feel, and what kind of stay do you
              want?
            </CardDescription>
          </CardHeader>

          <CardContent className="grid gap-6 sm:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="travel-style">Style</Label>
              <Controller
                control={control}
                name="travel_style"
                render={({ field }) => (
                  <Select
                    value={field.value}
                    onValueChange={field.onChange}
                  >
                    <SelectTrigger id="travel-style" className="w-full">
                      <SelectValue placeholder="Choose a style" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="relaxed">
                        Relaxed — plenty of breathing room
                      </SelectItem>
                      <SelectItem value="balanced">
                        Balanced — a mix of plans and downtime
                      </SelectItem>
                      <SelectItem value="adventurous">
                        Adventurous — active and varied
                      </SelectItem>
                    </SelectContent>
                  </Select>
                )}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="accommodation">Accommodation</Label>
              <Controller
                control={control}
                name="accommodation"
                render={({ field }) => (
                  <Select
                    value={field.value ?? "none"}
                    onValueChange={(value) =>
                      field.onChange(value === "none" ? null : value)
                    }
                  >
                    <SelectTrigger id="accommodation" className="w-full">
                      <SelectValue placeholder="No preference" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">No preference</SelectItem>
                      <SelectItem value="budget">Budget</SelectItem>
                      <SelectItem value="mid_range">Mid-range</SelectItem>
                      <SelectItem value="luxury">Luxury</SelectItem>
                    </SelectContent>
                  </Select>
                )}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="pace">Pace</Label>
              <Controller
                control={control}
                name="pace"
                render={({ field }) => (
                  <Select
                    value={field.value}
                    onValueChange={field.onChange}
                  >
                    <SelectTrigger id="pace" className="w-full">
                      <SelectValue placeholder="Choose a pace" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="slow">Slow</SelectItem>
                      <SelectItem value="moderate">Moderate</SelectItem>
                      <SelectItem value="fast">Fast</SelectItem>
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Interests</CardTitle>
            <CardDescription>
              Pick the things you would actually stop for. Selecting none is
              fine — the planner keeps the draft general.
            </CardDescription>
          </CardHeader>

          <CardContent>
            {interestsQuery.isPending ? (
              <LoadingState
                label="Loading interests…"
                className="py-6"
              />
            ) : interestsQuery.isError ? (
              <ErrorState
                title="Could not load interests"
                message={getErrorMessage(interestsQuery.error)}
                onRetry={() => {
                  void interestsQuery.refetch()
                }}
                className="py-6"
              />
            ) : interestsQuery.data.length === 0 ? (
              <p className="py-4 text-sm text-muted-foreground">
                The interest catalogue is empty on this server.
              </p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {interestsQuery.data.map((interest) => {
                  const selected = selectedInterestIds.includes(interest.id)

                  return (
                    <button
                      key={interest.id}
                      type="button"
                      aria-pressed={selected}
                      onClick={() => toggleInterest(interest.id)}
                      className={cn(
                        "rounded-full border px-3.5 py-1.5 text-sm transition-colors",
                        selected
                          ? "border-primary bg-primary text-primary-foreground"
                          : "bg-background text-muted-foreground hover:border-foreground/30 hover:text-foreground",
                      )}
                    >
                      {interest.name}
                    </button>
                  )
                })}
              </div>
            )}

            <p className="mt-4 text-xs text-muted-foreground">
              {selectedInterestIds.length} selected
            </p>
          </CardContent>
        </Card>

        {formError ? (
          <p className="rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2 text-sm text-destructive">
            {formError}
          </p>
        ) : null}

        <div className="flex items-center gap-3">
          <Button type="submit" disabled={saveMutation.isPending || !isDirty}>
            {saveMutation.isPending ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Saving…
              </>
            ) : (
              <>
                <Save className="size-4" />
                {preferences ? "Save preferences" : "Create preferences"}
              </>
            )}
          </Button>
          {isDirty ? (
            <span className="text-xs text-muted-foreground">
              Unsaved changes
            </span>
          ) : null}
        </div>
      </form>

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Clear these preferences?"
        description="The planner will fall back to a balanced plan until you add preferences again."
        confirmLabel="Clear preferences"
        destructive
        pending={deleteMutation.isPending}
        onConfirm={() => deleteMutation.mutate()}
      />
    </div>
  )
}
