import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Pencil, Plus, Receipt, Trash2 } from "lucide-react"
import { useMemo, useState } from "react"
import { toast } from "sonner"

import { deleteExpense, listExpenses } from "@/api/expenses"
import type { Expense } from "@/api/types"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { EmptyState } from "@/components/shared/empty-state"
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
import { categoryOption } from "@/features/expenses/categories"
import { ExpenseFormDialog } from "@/features/expenses/expense-form-dialog"
import { getErrorMessage } from "@/lib/api-error"
import { formatCurrency, formatDateShort } from "@/lib/format"
import { queryKeys } from "@/lib/query-keys"
import { cn } from "@/lib/utils"

function ExpenseSkeleton() {
  return (
    <div className="space-y-2" aria-hidden="true">
      {[0, 1, 2].map((index) => (
        <div key={index} className="h-12 animate-pulse rounded-lg bg-muted" />
      ))}
    </div>
  )
}

export function ExpenseCard({
  tripId,
  currency,
  className,
}: {
  tripId: string
  currency: string
  className?: string
}) {
  const queryClient = useQueryClient()

  const [addOpen, setAddOpen] = useState(false)
  const [editing, setEditing] = useState<Expense | null>(null)
  const [deleting, setDeleting] = useState<Expense | null>(null)

  const expensesQuery = useQuery({
    queryKey: queryKeys.expenses(tripId),
    queryFn: ({ signal }) => listExpenses(tripId, { signal }),
    enabled: Boolean(tripId),
  })

  const expenses = useMemo(
    () => expensesQuery.data?.expenses ?? [],
    [expensesQuery.data],
  )

  const summary = expensesQuery.data?.summary

  const totalSpent = Number(summary?.total_spent ?? 0)
  const budget = Number(summary?.budget ?? 0)

  const percentUsed =
    budget > 0 ? Math.min(100, Math.round((totalSpent / budget) * 100)) : 0

  const invalidateNotifications = () => {
    void queryClient.invalidateQueries({
      queryKey: queryKeys.notificationUnreadCount,
    })
    void queryClient.invalidateQueries({
      queryKey: queryKeys.notifications(false),
    })
  }

  const deleteMutation = useMutation({
    mutationFn: (expense: Expense) => deleteExpense(tripId, expense.id),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.expenses(tripId),
      })
      invalidateNotifications()
      toast.success("Expense removed.")
      setDeleting(null)
    },
    onError: (error) => {
      toast.error(getErrorMessage(error))
    },
  })

  const summaryCurrency = summary?.currency ?? currency

  return (
    <Card className={cn(className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Receipt className="size-4" />
          Expenses
        </CardTitle>
        <CardDescription>
          {summary
            ? `${summary.expense_count} ${
                summary.expense_count === 1 ? "expense" : "expenses"
              } recorded in ${summaryCurrency}`
            : "Track what you actually spend against the budget"}
        </CardDescription>

        <CardAction>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setAddOpen(true)}
          >
            <Plus className="size-4" />
            Add expense
          </Button>
        </CardAction>
      </CardHeader>

      <CardContent className="space-y-4">
        {expensesQuery.isPending ? (
          <ExpenseSkeleton />
        ) : expensesQuery.isError ? (
          <ErrorState
            title="Expenses unavailable"
            message={getErrorMessage(expensesQuery.error)}
            onRetry={() => {
              void expensesQuery.refetch()
            }}
          />
        ) : summary ? (
          <>
            <div className="space-y-3 rounded-lg border bg-muted/40 px-4 py-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <p className="text-sm">
                  <span className="font-heading text-2xl font-medium tabular-nums">
                    {formatCurrency(summary.total_spent, summaryCurrency)}
                  </span>
                  <span className="text-muted-foreground">
                    {" "}
                    of {formatCurrency(summary.budget, summaryCurrency)}
                  </span>
                </p>
                <p
                  className={cn(
                    "text-xs font-medium",
                    summary.over_budget
                      ? "text-destructive"
                      : "text-muted-foreground",
                  )}
                >
                  {summary.over_budget
                    ? `${formatCurrency(
                        Math.abs(Number(summary.remaining)),
                        summaryCurrency,
                      )} over budget`
                    : `${formatCurrency(
                        summary.remaining,
                        summaryCurrency,
                      )} left`}
                </p>
              </div>

              <div
                className="h-2 overflow-hidden rounded-full bg-background ring-1 ring-foreground/10"
                role="progressbar"
                aria-label="Share of the budget spent"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={percentUsed}
              >
                <div
                  className={cn(
                    "h-full rounded-full transition-all",
                    summary.over_budget ? "bg-destructive" : "bg-primary",
                  )}
                  style={{ width: `${percentUsed}%` }}
                />
              </div>

              {summary.by_category.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {summary.by_category.map((row) => {
                    const option = categoryOption(row.category)

                    return (
                      <Badge
                        key={row.category}
                        variant="outline"
                        className="gap-1 bg-background"
                      >
                        <option.icon className="size-3" />
                        {option.label}
                        <span className="text-muted-foreground">
                          {formatCurrency(row.total, summaryCurrency)}
                        </span>
                      </Badge>
                    )
                  })}
                </div>
              ) : null}
            </div>

            {expenses.length > 0 ? (
              <ul className="divide-y rounded-lg border">
                {expenses.map((expense) => {
                  const option = categoryOption(expense.category)

                  return (
                    <li
                      key={expense.id}
                      className="flex items-center gap-3 px-3 py-2.5"
                    >
                      <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-muted text-muted-foreground">
                        <option.icon className="size-4" />
                      </span>

                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium">
                          {expense.title}
                        </p>
                        <p className="truncate text-xs text-muted-foreground">
                          {option.label} ·{" "}
                          {formatDateShort(expense.spent_on)}
                          {expense.notes ? ` · ${expense.notes}` : ""}
                        </p>
                      </div>

                      <span className="shrink-0 text-sm font-medium tabular-nums">
                        {formatCurrency(expense.amount, summaryCurrency)}
                      </span>

                      <div className="flex shrink-0 items-center">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-8"
                          aria-label={`Edit ${expense.title}`}
                          onClick={() => setEditing(expense)}
                        >
                          <Pencil className="size-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-8 text-muted-foreground hover:text-destructive"
                          aria-label={`Delete ${expense.title}`}
                          onClick={() => setDeleting(expense)}
                        >
                          <Trash2 className="size-3.5" />
                        </Button>
                      </div>
                    </li>
                  )
                })}
              </ul>
            ) : (
              <EmptyState
                icon={<Receipt className="size-5" />}
                title="No expenses yet"
                description="Add what you have already paid for — transport, stays, food — and the total updates against your budget."
                className="py-8"
                action={
                  <Button size="sm" onClick={() => setAddOpen(true)}>
                    <Plus className="size-4" />
                    Add the first expense
                  </Button>
                }
              />
            )}
          </>
        ) : null}
      </CardContent>

      <ExpenseFormDialog
        open={addOpen}
        onOpenChange={setAddOpen}
        tripId={tripId}
        currency={summaryCurrency}
      />

      <ExpenseFormDialog
        open={editing !== null}
        onOpenChange={(open) => {
          if (!open) {
            setEditing(null)
          }
        }}
        tripId={tripId}
        currency={summaryCurrency}
        expense={editing ?? undefined}
      />

      <ConfirmDialog
        open={deleting !== null}
        onOpenChange={(open) => {
          if (!open) {
            setDeleting(null)
          }
        }}
        title="Delete this expense?"
        description={
          deleting
            ? `“${deleting.title}” will be removed and your totals recalculated.`
            : ""
        }
        confirmLabel="Delete expense"
        destructive
        pending={deleteMutation.isPending}
        onConfirm={() => {
          if (deleting) {
            deleteMutation.mutate(deleting)
          }
        }}
      />
    </Card>
  )
}
