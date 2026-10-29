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
  features/    trip and itinerary dialogs and cards
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
- **Timeouts.** 30 s by default, 60 s for place search, 180 s for AI generation.
  These match how slow the real providers are; neither call streams.
- **Interests.** The form loads the catalogue from `GET /api/v1/interests/`
  instead of hardcoding IDs.
- **Generation.** `POST .../itinerary/generate/` is called directly (no
  `dry_run` preview, which would double a 60–130 s run). When an itinerary
  already exists the UI asks for confirmation before sending `replace=true`.

## Known limitations

- Place search and AI generation depend on the public Overpass API and a local
  Ollama instance. When either is down the UI shows a retryable error and
  leaves existing data untouched.
- The production bundle is a single chunk (~830 kB, ~255 kB gzipped). Route-level
  code splitting is the obvious next step.
- There are no frontend unit tests yet; behaviour is verified manually against
  the live API, and the backend suite covers the endpoints themselves.
