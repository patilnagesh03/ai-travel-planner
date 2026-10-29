import { createBrowserRouter, Navigate } from "react-router-dom"

import { ProtectedRoute, PublicOnlyRoute } from "@/auth/route-guards"
import { AppLayout } from "@/components/layout/app-layout"
import { ItineraryPage } from "@/pages/itinerary-page"
import { NotFoundPage } from "@/pages/not-found-page"
import { PlacesPage } from "@/pages/places-page"
import { PreferencesPage } from "@/pages/preferences-page"
import { ProfilePage } from "@/pages/profile-page"
import { SignInPage } from "@/pages/sign-in-page"
import { SignUpPage } from "@/pages/sign-up-page"
import { TripDetailPage } from "@/pages/trip-detail-page"
import { TripsPage } from "@/pages/trips-page"

export const router = createBrowserRouter([
  {
    path: "/signin",
    element: (
      <PublicOnlyRoute>
        <SignInPage />
      </PublicOnlyRoute>
    ),
  },
  {
    path: "/signup",
    element: (
      <PublicOnlyRoute>
        <SignUpPage />
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
