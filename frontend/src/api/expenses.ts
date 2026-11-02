import { api } from "@/api/client"
import type {
  ApiEnvelope,
  Expense,
  ExpenseCategory,
  ExpenseList,
  ExpensePayload,
} from "@/api/types"
import { unwrap } from "@/lib/envelope"

export async function listExpenses(
  tripId: string,
  options: { category?: ExpenseCategory; signal?: AbortSignal } = {},
): Promise<ExpenseList> {
  const { category, signal } = options

  const response = await api.get<ApiEnvelope<ExpenseList>>(
    `/api/v1/trips/${tripId}/expenses/`,
    {
      signal,
      params: category ? { category } : undefined,
    },
  )

  return unwrap(response.data)
}

export async function createExpense(
  tripId: string,
  payload: ExpensePayload,
): Promise<Expense> {
  const response = await api.post<ApiEnvelope<Expense>>(
    `/api/v1/trips/${tripId}/expenses/`,
    payload,
  )

  return unwrap(response.data)
}

export async function updateExpense(
  tripId: string,
  expenseId: string,
  payload: Partial<ExpensePayload>,
): Promise<Expense> {
  const response = await api.patch<ApiEnvelope<Expense>>(
    `/api/v1/trips/${tripId}/expenses/${expenseId}/`,
    payload,
  )

  return unwrap(response.data)
}

export async function deleteExpense(
  tripId: string,
  expenseId: string,
): Promise<void> {
  await api.delete(`/api/v1/trips/${tripId}/expenses/${expenseId}/`)
}
