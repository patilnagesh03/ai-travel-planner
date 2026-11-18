import { lazy, Suspense } from "react"
import { createBrowserRouter, Navigate } from "react-router-dom"

import { ProtectedRoute, PublicOnlyRoute } from "@/auth/route-guards"
import { AppLayout } from "@/components/layout/app-layout"
import { FullPageLoader } from "@/components/shared/full-page-loader"
import { NotFoundPage } from "@/pages/not-found-page"

// Every route is loaded on demand so the first paint only pays for the shell,
// the header and the page the visitor actually asked for.
const SignInPage = lazy(() =>
  import("@/pages/sign-in-page").then((module) => ({
    default: module.SignInPage,
  })),
)

const SignUpPage = lazy(() =>
  import("@/pages/sign-up-page").then((module) => ({
    default: module.SignUpPage,
  })),
)

const TripsPage = lazy(() =>
  import("@/pages/trips-page").then((module) => ({
    default: module.TripsPage,
  })),
)

const TripDetailPage = lazy(() =>
  import("@/pages/trip-detail-page").then((module) => ({
    default: module.TripDetailPage,
  })),
)

const PreferencesPage = lazy(() =>
  import("@/pages/preferences-page").then((module) => ({
    default: module.PreferencesPage,
  })),
)

const PlacesPage = lazy(() =>
  import("@/pages/places-page").then((module) => ({
    default: module.PlacesPage,
  })),
)

const ItineraryPage = lazy(() =>
  import("@/pages/itinerary-page").then((module) => ({
    default: module.ItineraryPage,
  })),
)

const ProfilePage = lazy(() =>
  import("@/pages/profile-page").then((module) => ({
    default: module.ProfilePage,
  })),
)

export const router = createBrowserRouter([
  {
    path: "/signin",
    element: (
      <PublicOnlyRoute>
        <Suspense fallback={<FullPageLoader />}>
          <SignInPage />
        </Suspense>
      </PublicOnlyRoute>
    ),
  },
  {
    path: "/signup",
    element: (
      <PublicOnlyRoute>
        <Suspense fallback={<FullPageLoader />}>
          <SignUpPage />
        </Suspense>
      </PublicOnlyRoute>
    ),
  },
  {
    path: "/",
    element: (
      <ProtectedRoute>
        <AppLayout />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: <Navigate to="/trips" replace />,
      },
      {
        path: "trips",
        element: <TripsPage />,
      },
      {
        path: "trips/:tripId",
        element: <TripDetailPage />,
      },
      {
        path: "trips/:tripId/preferences",
        element: <PreferencesPage />,
      },
      {
        path: "trips/:tripId/places",
        element: <PlacesPage />,
      },
      {
        path: "trips/:tripId/itinerary",
        element: <ItineraryPage />,
      },
      {
        path: "profile",
        element: <ProfilePage />,
      },
    ],
  },
  {
    path: "*",
    element: <NotFoundPage />,
  },
])
