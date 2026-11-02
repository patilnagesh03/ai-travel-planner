# AI Travel Planner — frontend

React 19 + TypeScript single-page app for the Django backend in `../backend`.

## Requirements

- Node.js 20+ and npm
- The Django API running locally (default `http://127.0.0.1:8000`)

## Setup

```bash
npm install
cp .env.example .env      # PowerShell: Copy-Item .env.example .env
npm run dev               # http://localhost:5173
```

`VITE_API_BASE_URL` is the only required variable. It must point at the Django
API root, not at `/api`.

## Scripts

| Script            | What it does                                  |
| ----------------- | --------------------------------------------- |
| `npm run dev`     | Vite dev server with HMR                      |
| `npm run build`   | Type-check (`tsc -b`) and build to `dist/`    |
| `npm run lint`    | Oxlint                                        |
| `npm run preview` | Serve the production build locally            |

## Structure

```
src/
  api/         typed API modules, Axios client, shared types
  auth/        session bootstrap, token storage, route guards
  components/  layout, shared states and shadcn/ui primitives
  features/    trip, itinerary, weather, currency, map, expenses, notifications
  lib/         envelope unwrapping, query keys, formatting, errors
  pages/       one component per route
```

## Design notes

- **Tokens.** The access token lives in memory only; the refresh token is kept
  in `localStorage` so a reload restores the session. The Axios client attaches
  the access token, performs a single-flight refresh on 401, rotates the stored
  refresh token and retries the original request once. A failed refresh clears
  the session and redirects to `/signin`.
- **Response envelopes.** Most endpoints return `{success, message, data}` while
  itinerary PATCH and the itinerary-item endpoints return bare objects. Both are
  normalised in `src/lib/envelope.ts` rather than reshaping backend responses.
- **Timeouts.** 30 s by default, 60 s for place search, 20 s for weather, 15 s
  for exchange rates and 180 s for AI generation. These match how slow the real
  providers are; none of them streams.
- **Interests.** The form loads the catalogue from `GET /api/v1/interests/`
  instead of hardcoding IDs.
- **Generation.** `POST .../itinerary/generate/` is called directly (no
  `dry_run` preview, which would double a 60–130 s run). When an itinerary
  already exists the UI asks for confirmation before sending `replace=true`.
- **Weather, rates and maps.** The trip page shows a trip-scoped forecast
  (Open-Meteo), an INR converter (Frankfurter/ECB) and an OpenStreetMap panel.
  The map reuses `GET /api/v1/places/resolve/` for the destination so the
  frontend does not duplicate the backend's alias and state rules. Leaflet's
  default image markers are avoided in favour of `CircleMarker`, which needs no
  runtime asset resolution. The map wrapper is `isolate`d so Leaflet's pane
  z-indices cannot cover dialogs or menus.
- **Expenses.** The trip page keeps a list and its totals in a single query:
  `GET .../expenses/` returns both, so the progress bar cannot drift from the
  rows below it. Every expense is in the trip's currency. Create and edit share
  one dialog; deleting asks first, and each mutation refreshes the expense
  query plus both notification queries because crossing the budget can add a
  bell item immediately.
- **Notifications.** The bell uses two queries. The unread count polls every
  60 s and drives the badge; the list is only fetched when the popover opens.
  Opening an item marks it read and navigates to its trip; "mark all read" and
  dismissing refresh the badge and the list. The backend derives notifications
  from trip and expense state, so the client never creates them.
- **Currencies.** The converter fetches all 11 offered currencies in one
  request and switches target locally. The list is limited to codes Frankfurter
  actually publishes: a single unsupported code would make the whole batch
  unusable, because the provider silently omits it.

## Known limitations

- Place search and AI generation depend on the public Overpass API and a local
  Ollama instance. When either is down the UI shows a retryable error and
  leaves existing data untouched.
- Weather, currency and map tiles depend on Open-Meteo, Frankfurter and
  `tile.openstreetmap.org`. Each card reports its own failure without taking
  the page down; the rest of the trip page keeps working.
- Expense summaries are trip-wide by design; the category filter narrows the
  rows but not the totals. A budget-exceeded notification is re-armed only when
  the budget changes, so its message can lag further spending until it is
  dismissed.
- The production bundle is a single chunk (~1.02 MB, ~310 kB gzipped). Leaflet is
  the largest addition. Route-level code splitting, or lazily loading the map
  components, is the obvious next step.
- There are no frontend unit tests yet; behaviour is verified manually against
  the live API, and the backend suite covers the endpoints themselves.
