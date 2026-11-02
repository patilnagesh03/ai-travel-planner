import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Loader2 } from "lucide-react"
import { useEffect, useState } from "react"
import { Controller, useForm } from "react-hook-form"
import { toast } from "sonner"
import { z } from "zod"

import { createExpense, updateExpense } from "@/api/expenses"
import type { Expense } from "@/api/types"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { EXPENSE_CATEGORIES } from "@/features/expenses/categories"
import { getErrorMessage } from "@/lib/api-error"
import { currentDateInputValue } from "@/lib/format"
import { queryKeys } from "@/lib/query-keys"

const expenseSchema = z.object({
  title: z.string().trim().min(1, "What did you pay for?"),
  amount: z
    .string()
    .min(1, "Enter an amount.")
    .refine(
      (value) => Number.isFinite(Number(value)) && Number(value) > 0,
      "Amount must be greater than zero.",
    ),
  category: z.enum([
    "transport",
    "stay",
    "food",
    "activities",
    "shopping",
    "other",
  ]),
  spent_on: z.string().min(1, "Pick a date."),
  notes: z.string().optional(),
})

type ExpenseFormValues = z.infer<typeof expenseSchema>

function formValues(expense?: Expense): ExpenseFormValues {
  if (expense) {
    return {
      title: expense.title,
      amount: expense.amount,
      category: expense.category,
      spent_on: expense.spent_on,
      notes: expense.notes ?? "",
    }
  }

  return {
    title: "",
    amount: "",
    category: "food",
    spent_on: currentDateInputValue(),
    notes: "",
  }
}

export function ExpenseFormDialog({
  open,
  onOpenChange,
  tripId,
  currency,
  expense,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  tripId: string
  currency: string
  expense?: Expense
}) {
  const queryClient = useQueryClient()
  const [formError, setFormError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    control,
    formState: { errors },
  } = useForm<ExpenseFormValues>({
    resolver: zodResolver(expenseSchema),
    defaultValues: formValues(expense),
  })

  useEffect(() => {
    if (open) {
      reset(formValues(expense))
      setFormError(null)
    }
  }, [open, expense, reset])

  const mutation = useMutation({
    mutationFn: (values: ExpenseFormValues) => {
      const payload = {
        title: values.title.trim(),
        amount: values.amount,
        category: values.category,
        spent_on: values.spent_on,
        notes: values.notes?.trim() || null,
      }

      return expense
        ? updateExpense(tripId, expense.id, payload)
        : createExpense(tripId, payload)
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.expenses(tripId),
      })

      // Recording an expense can cross the budget, so the bell may have a
      // new item before this dialog even closes.
      void queryClient.invalidateQueries({
        queryKey: queryKeys.notificationUnreadCount,
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.notifications(false),
      })

      toast.success(expense ? "Expense updated." : "Expense added.")
      onOpenChange(false)
    },
    onError: (error) => {
      setFormError(getErrorMessage(error))
    },
  })

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!mutation.isPending) {
          onOpenChange(nextOpen)
        }
      }}
    >
      <DialogContent className="max-h-[90svh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{expense ? "Edit expense" : "Add an expense"}</DialogTitle>
          <DialogDescription>
            Amounts are recorded in {currency}, the trip&apos;s currency.
          </DialogDescription>
        </DialogHeader>

        <form
          className="space-y-4"
          onSubmit={handleSubmit((values) => mutation.mutate(values))}
          noValidate
        >
          <div className="space-y-2">
            <Label htmlFor="expense-title">What did you pay for?</Label>
            <Input
              id="expense-title"
              placeholder="Dinner at Laxmi Mishthan Bhandar"
              aria-invalid={!!errors.title}
              {...register("title")}
            />
            {errors.title ? (
              <p className="text-sm text-destructive">{errors.title.message}</p>
            ) : null}
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="expense-amount">Amount ({currency})</Label>
              <Input
                id="expense-amount"
                type="number"
                min="0"
                step="0.01"
                inputMode="decimal"
                placeholder="450"
                aria-invalid={!!errors.amount}
                {...register("amount")}
              />
              {errors.amount ? (
                <p className="text-sm text-destructive">
                  {errors.amount.message}
                </p>
              ) : null}
            </div>

            <div className="space-y-2">
              <Label htmlFor="expense-category">Category</Label>
              <Controller
                control={control}
                name="category"
                render={({ field }) => (
                  <Select
                    value={field.value}
                    onValueChange={field.onChange}
                  >
                    <SelectTrigger id="expense-category" className="w-full">
                      <SelectValue placeholder="Choose a category" />
                    </SelectTrigger>
                    <SelectContent>
                      {EXPENSE_CATEGORIES.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              {errors.category ? (
                <p className="text-sm text-destructive">
                  {errors.category.message}
                </p>
              ) : null}
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="expense-date">Date</Label>
            <Input
              id="expense-date"
              type="date"
              aria-invalid={!!errors.spent_on}
              {...register("spent_on")}
            />
            {errors.spent_on ? (
              <p className="text-sm text-destructive">
                {errors.spent_on.message}
              </p>
            ) : null}
          </div>

          <div className="space-y-2">
            <Label htmlFor="expense-notes">Notes</Label>
            <Textarea
              id="expense-notes"
              rows={2}
              placeholder="Optional — split with friends, paid by card, etc."
              {...register("notes")}
            />
          </div>

          {formError ? (
            <p className="rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              {formError}
            </p>
          ) : null}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              disabled={mutation.isPending}
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  Saving…
                </>
              ) : expense ? (
                "Save changes"
              ) : (
                "Add expense"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
