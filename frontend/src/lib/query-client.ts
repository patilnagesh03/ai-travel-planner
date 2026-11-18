import { QueryClient } from "@tanstack/react-query"

import { getErrorStatus } from "@/lib/api-error"

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      retry: (failureCount, error) => {
        const status = getErrorStatus(error)

        // Do not retry auth, permission, missing-resource or conflict errors.
        if (status && status >= 400 && status < 500 && status !== 429) {
          return false
        }

        return failureCount < 1
      },
    },
    mutations: {
      retry: 0,
    },
  },
})
