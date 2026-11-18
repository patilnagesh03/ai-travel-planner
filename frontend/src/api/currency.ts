import { api } from "@/api/client"
import type { ApiEnvelope, CurrencyRates } from "@/api/types"
import { unwrap } from "@/lib/envelope"

const CURRENCY_TIMEOUT = 15_000

export async function getCurrencyRates(
  base: string,
  symbols: string[],
  signal?: AbortSignal,
): Promise<CurrencyRates> {
  const response = await api.get<ApiEnvelope<CurrencyRates>>(
    "/api/v1/currency/rates/",
    {
      timeout: CURRENCY_TIMEOUT,
      signal,
      params: {
        base,
        symbols: symbols.join(","),
      },
    },
  )

  return unwrap(response.data)
}
