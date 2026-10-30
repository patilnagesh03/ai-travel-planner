import { useQuery } from "@tanstack/react-query"
import {
  Cloud,
  CloudDrizzle,
  CloudFog,
  CloudLightning,
  CloudRain,
  CloudSnow,
  CloudSun,
  Droplets,
  Sun,
} from "lucide-react"

import { getTripWeather } from "@/api/weather"
import { ErrorState } from "@/components/shared/error-state"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { getErrorMessage } from "@/lib/api-error"
import {
  formatDateShort,
  formatWeekdayShort,
} from "@/lib/format"
import { queryKeys } from "@/lib/query-keys"
import { cn } from "@/lib/utils"

function WeatherIcon({
  code,
  className,
}: {
  code: number | null
  className?: string
}) {
  const Icon = (() => {
    if (code === 0) {
      return Sun
    }

    if (code === 1 || code === 2) {
      return CloudSun
    }

    if (code === 3) {
      return Cloud
    }

    if (code === 45 || code === 48) {
      return CloudFog
    }

    if (code !== null && code >= 51 && code <= 57) {
      return CloudDrizzle
    }

    if (
      code !== null &&
      ((code >= 61 && code <= 67) || (code >= 80 && code <= 82))
    ) {
      return CloudRain
    }

    if (
      code !== null &&
      ((code >= 71 && code <= 77) || code === 85 || code === 86)
    ) {
      return CloudSnow
    }

    if (code !== null && code >= 95) {
      return CloudLightning
    }

    return Cloud
  })()

  return <Icon className={className} />
}

function formatTemperature(value: number | null): string {
  return value === null ? "—" : `${Math.round(value)}°`
}

function WeatherSkeleton() {
  return (
    <div className="flex gap-3 overflow-hidden" aria-hidden="true">
      {[0, 1, 2, 3, 4].map((index) => (
        <div
          key={index}
          className="h-40 min-w-28 flex-1 animate-pulse rounded-lg bg-muted"
        />
      ))}
    </div>
  )
}

export function WeatherCard({
  tripId,
  className,
}: {
  tripId: string
  className?: string
}) {
  const weatherQuery = useQuery({
    queryKey: queryKeys.weather(tripId),
    queryFn: ({ signal }) => getTripWeather(tripId, signal),
    enabled: Boolean(tripId),
    // The backend caches the provider response for 15 minutes.
    staleTime: 10 * 60_000,
  })

  const weather = weatherQuery.data

  return (
    <Card className={cn(className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <CloudSun className="size-4" />
          Weather
        </CardTitle>
        <CardDescription>
          {weather?.destination.name
            ? `${weather.destination.name}, ${weather.destination.state}`
            : "Daily forecast for your travel dates"}
          {weather && weather.trip_days > 0
            ? ` · covers ${weather.covered_days} of ${weather.trip_days} ${
                weather.trip_days === 1 ? "day" : "days"
              }`
            : ""}
        </CardDescription>

        {weather && weather.days.length > 0 ? (
          <CardAction>
            <Badge variant="outline">
              {weather.days.length}{" "}
              {weather.days.length === 1 ? "day" : "days"}
            </Badge>
          </CardAction>
        ) : null}
      </CardHeader>

      <CardContent className="space-y-4">
        {weatherQuery.isPending ? (
          <WeatherSkeleton />
        ) : weatherQuery.isError ? (
          <ErrorState
            title="Forecast unavailable"
            message={getErrorMessage(weatherQuery.error)}
            onRetry={() => {
              void weatherQuery.refetch()
            }}
          />
        ) : weather && weather.days.length > 0 ? (
          <>
            <div className="flex gap-3 overflow-x-auto pb-1">
              {weather.days.map((day) => (
                <div
                  key={day.date}
                  className="flex min-w-28 flex-1 flex-col gap-2 rounded-lg border bg-background px-3 py-3"
                  title={
                    day.wind_speed_max === null
                      ? day.condition
                      : `${day.condition} · wind up to ${Math.round(
                          day.wind_speed_max,
                        )} ${weather.units.wind_speed}`
                  }
                >
                  <div>
                    <p className="text-xs font-medium">
                      {formatWeekdayShort(day.date)}
                    </p>
                    <p className="text-[11px] text-muted-foreground">
                      {formatDateShort(day.date)}
                    </p>
                  </div>

                  <WeatherIcon
                    code={day.weather_code}
                    className="size-6 text-muted-foreground"
                  />

                  <p className="line-clamp-2 text-xs text-muted-foreground">
                    {day.condition}
                  </p>

                  <p className="text-sm">
                    <span className="font-medium">
                      {formatTemperature(day.temperature_max)}
                    </span>
                    <span className="text-muted-foreground">
                      {" "}
                      / {formatTemperature(day.temperature_min)}
                    </span>
                  </p>

                  <p className="flex items-center gap-1 text-[11px] text-muted-foreground">
                    <Droplets className="size-3" />
                    {day.precipitation_probability === null
                      ? "—"
                      : `${day.precipitation_probability}%`}
                  </p>
                </div>
              ))}
            </div>

            <div className="flex flex-wrap items-start justify-between gap-2 text-[11px] text-muted-foreground">
              <span>
                {weather.note ??
                  `${formatDateShort(
                    weather.forecast_window.starts_on,
                  )} – ${formatDateShort(weather.forecast_window.ends_on)}`}
              </span>
              <span>{weather.attribution}</span>
            </div>
          </>
        ) : weather ? (
          <div className="flex flex-col gap-4 rounded-lg border border-dashed px-4 py-8 text-center">
            <p className="mx-auto max-w-md text-sm text-muted-foreground">
              {weather.note ??
                "The forecast does not cover these dates yet. Check back closer to the trip."}
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mx-auto"
              onClick={() => {
                void weatherQuery.refetch()
              }}
            >
              Refresh forecast
            </Button>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
