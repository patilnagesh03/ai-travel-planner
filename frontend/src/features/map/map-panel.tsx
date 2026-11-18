import L from "leaflet"
import "leaflet/dist/leaflet.css"
import { useEffect, useMemo } from "react"
import {
  CircleMarker,
  MapContainer,
  Popup,
  TileLayer,
  Tooltip,
  useMap,
} from "react-leaflet"

import { cn } from "@/lib/utils"

/**
 * OSM's tile usage policy requires attribution. The link is also shown in the
 * map's own attribution control, which keeps the credit visible when the map
 * is embedded in a card.
 */
const TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"

const ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'

export interface MapMarker {
  id: string
  latitude: number
  longitude: number
  title: string
  description?: string | null
  /** The destination is drawn larger than its surrounding stops. */
  emphasis?: boolean
}

interface MapPanelProps {
  center: { latitude: number; longitude: number }
  markers?: MapMarker[]
  zoom?: number
  height?: number
  className?: string
  ariaLabel?: string
}

function MapViewport({
  center,
  markers,
  zoom,
}: {
  center: [number, number]
  markers: MapMarker[]
  zoom: number
}) {
  const map = useMap()

  useEffect(() => {
    if (markers.length > 1) {
      map.fitBounds(
        L.latLngBounds(
          markers.map(
            (marker) => [marker.latitude, marker.longitude] as [number, number],
          ),
        ),
        { padding: [32, 32], maxZoom: 15 },
      )

      return
    }

    if (markers.length === 1) {
      map.setView([markers[0].latitude, markers[0].longitude], zoom + 2)

      return
    }

    map.setView(center, zoom)
  }, [map, center, markers, zoom])

  return null
}

/**
 * A read-only OpenStreetMap panel.
 *
 * Circles are used instead of the default Leaflet marker images: the marker
 * icons resolve their image URLs at runtime, which is a common source of
 * missing-pin bugs in bundlers. A circle needs no asset and is enough here.
 */
export function MapPanel({
  center,
  markers = [],
  zoom = 11,
  height = 320,
  className,
  ariaLabel = "Map",
}: MapPanelProps) {
  const centerTuple = useMemo<[number, number]>(
    () => [center.latitude, center.longitude],
    [center.latitude, center.longitude],
  )

  return (
    <div
      role="region"
      aria-label={ariaLabel}
      // `isolate` keeps Leaflet's high z-index panes inside this card so they
      // cannot cover dialogs, dropdowns or the sticky header.
      className={cn(
        "relative isolate overflow-hidden rounded-lg ring-1 ring-foreground/10",
        className,
      )}
      style={{ height }}
    >
      <MapContainer
        center={centerTuple}
        zoom={zoom}
        scrollWheelZoom={false}
        style={{ height: "100%", width: "100%" }}
      >
        <TileLayer url={TILE_URL} attribution={ATTRIBUTION} />

        <MapViewport
          center={centerTuple}
          markers={markers}
          zoom={zoom}
        />

        {markers.map((marker) => (
          <CircleMarker
            key={marker.id}
            center={[marker.latitude, marker.longitude]}
            radius={marker.emphasis ? 9 : 7}
            pathOptions={{
              color: marker.emphasis ? "#1d4ed8" : "#0f766e",
              fillColor: marker.emphasis ? "#3b82f6" : "#14b8a6",
              fillOpacity: 0.9,
              weight: 2,
            }}
          >
            <Tooltip direction="top" offset={[0, -8]} opacity={1}>
              {marker.title}
            </Tooltip>
            <Popup>
              <div className="space-y-1">
                <p className="font-medium">{marker.title}</p>
                {marker.description ? (
                  <p className="text-xs text-muted-foreground">
                    {marker.description}
                  </p>
                ) : null}
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  )
}
