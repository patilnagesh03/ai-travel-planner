import { useQuery } from "@tanstack/react-query"
import { ArrowLeftRight } from "lucide-react"
import { useMemo, useState } from "react"

import { getCurrencyRates } from "@/api/currency"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { getErrorMessage } from "@/lib/api-error"
import { queryKeys } from "@/lib/query-keys"
import { cn } from "@/lib/utils"

/**
 * The currencies a traveller is most likely to need. Kept inside the
 * backend's MAX_CURRENCY_SYMBOLS (12) so one request fetches them all and
 * switching the target needs no new network call.
 *
 * Only currencies the provider actually publishes belong here: Frankfurter
 * answers 200 but omits unknown codes, and a single unsupported code would
 * make the whole request unusable. That is why, for example, AED is absent.
 */
const CURRENCIES = [
  { code: "INR", label: "Indian rupee" },
  { code: "USD", label: "US dollar" },
  { code: "EUR", label: "Euro" },
  { code: "GBP", label: "British pound" },
  { code: "SGD", label: "Singapore dollar" },
  { code: "AUD", label: "Australian dollar" },
  { code: "CAD", label: "Canadian dollar" },
  { code: "JPY", label: "Japanese yen" },
  { code: "THB", label: "Thai baht" },
  { code: "MYR", label: "Malaysian ringgit" },
  { code: "CHF", label: "Swiss franc" },
] as const

function toInputValue(value: string | number): string {
  const numeric = typeof value === "number" ? value : Number(value)

  return Number.isFinite(numeric) ? String(numeric) : ""
}

function formatMoney(value: number, currency: string): string {
  try {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency,
      maximumFractionDigits: 2,
    }).format(value)
  } catch {
    return `${currency} ${value.toFixed(2)}`
  }
}

function formatRate(value: number): string {
  return new Intl.NumberFormat("en-IN", {
    maximumSignificantDigits: 6,
  }).format(value)
}

export function CurrencyConverter({
  baseCurrency,
  amount,
  className,
}: {
  baseCurrency: string
  amount: string | number
  className?: string
}) {
  const base = baseCurrency.trim().toUpperCase() || "INR"

  const options = useMemo(
    () => CURRENCIES.filter((currency) => currency.code !== base),
    [base],
  )

  const [target, setTarget] = useState<string>(
    () => options[0]?.code ?? "USD",
  )
  const [amountValue, setAmountValue] = useState(() =>
    toInputValue(amount),
  )
  const [syncedAmount, setSyncedAmount] = useState(amount)

  // A trip's budget can change while this card is mounted. Adjusting state
  // during render is React's documented pattern for a changed prop, and
  // unlike an effect it does not render once with the stale amount.
  if (amount !== syncedAmount) {
    setSyncedAmount(amount)
    setAmountValue(toInputValue(amount))
  }

  // If the trip currency changes, a target that now equals the base is no
  // longer offerable. Deriving the active value keeps the list consistent
  // without a second state update.
  const activeTarget = options.some((currency) => currency.code === target)
    ? target
    : options[0]?.code ?? "USD"

  const symbols = useMemo(
    () => options.map((currency) => currency.code),
    [options],
  )

  const ratesQuery = useQuery({
    queryKey: queryKeys.currencyRates(base, symbols),
    queryFn: ({ signal }) => getCurrencyRates(base, symbols, signal),
    enabled: symbols.length > 0,
    // The provider publishes once per working day; the backend caches for
    // an hour on top of that.
    staleTime: 30 * 60_000,
  })

  const rate = ratesQuery.data?.rates[activeTarget]

  const numericAmount = Number(amountValue)
  const hasValidAmount =
    amountValue.trim() !== "" &&
    Number.isFinite(numericAmount) &&
    numericAmount >= 0

  const converted =
    hasValidAmount && rate !== undefined ? numericAmount * rate : null

  return (
    <Card className={cn(className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <ArrowLeftRight className="size-4" />
          Currency converter
        </CardTitle>
        <CardDescription>
          Reference rates from {base}. Useful for checking prices before you
          book.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="currency-amount">Amount ({base})</Label>
            <Input
              id="currency-amount"
              type="number"
              min="0"
              step="0.01"
              inputMode="decimal"
              value={amountValue}
              onChange={(event) => setAmountValue(event.target.value)}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="currency-target">Convert to</Label>
            <Select value={activeTarget} onValueChange={setTarget}>
              <SelectTrigger id="currency-target" className="w-full">
                <SelectValue placeholder="Choose a currency" />
              </SelectTrigger>
              <SelectContent>
                {options.map((currency) => (
                  <SelectItem key={currency.code} value={currency.code}>
                    {currency.code} — {currency.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {ratesQuery.isPending ? (
          <div className="h-24 animate-pulse rounded-lg bg-muted" />
        ) : ratesQuery.isError ? (
          <div className="flex flex-col items-start gap-2 rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-3 text-sm">
            <p className="text-destructive">
              {getErrorMessage(ratesQuery.error)}
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                void ratesQuery.refetch()
              }}
            >
              Try again
            </Button>
          </div>
        ) : !hasValidAmount ? (
          <p className="rounded-lg border border-dashed px-3 py-6 text-center text-sm text-muted-foreground">
            Enter an amount to convert.
          </p>
        ) : rate === undefined ? (
          <p className="rounded-lg border border-dashed px-3 py-6 text-center text-sm text-muted-foreground">
            No rate is available for {activeTarget} right now.
          </p>
        ) : (
          <div className="space-y-2 rounded-lg bg-muted/50 px-4 py-4">
            <p className="text-xs text-muted-foreground">
              {formatMoney(numericAmount, base)} is about
            </p>
            <p className="font-heading text-2xl font-medium tabular-nums">
              {converted === null ? "—" : formatMoney(converted, activeTarget)}
            </p>
            <p className="text-xs text-muted-foreground">
              1 {base} = {formatRate(rate)} {activeTarget}
              {ratesQuery.data.date ? ` · ${ratesQuery.data.date}` : ""}
            </p>
          </div>
        )}

        {ratesQuery.data ? (
          <p className="text-right text-[11px] text-muted-foreground">
            {ratesQuery.data.attribution}
          </p>
        ) : null}
      </CardContent>
    </Card>
  )
}
