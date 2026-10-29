import { api } from "@/api/client"
import type {
  AiStatus,
  ApiEnvelope,
  GenerationPayload,
  GenerationResult,
} from "@/api/types"
import { unwrap } from "@/lib/envelope"

/**
 * A full generation (Overpass search + local model inference) takes roughly
 * 60–130 seconds on the development setup. The request has no streaming, so
 * the client timeout must be generous.
 */
const GENERATION_TIMEOUT = 180_000

export async function generateItinerary(
  tripId: string,
  payload: GenerationPayload,
): Promise<GenerationResult> {
  const response = await api.post<ApiEnvelope<GenerationResult>>(
    `/api/v1/trips/${tripId}/itinerary/generate/`,
    payload,
    { timeout: GENERATION_TIMEOUT },
  )

  return unwrap(response.data)
}

export async function getAiStatus(): Promise<AiStatus> {
  const response = await api.get<ApiEnvelope<AiStatus>>("/api/v1/ai/status/")

  return unwrap(response.data)
}
