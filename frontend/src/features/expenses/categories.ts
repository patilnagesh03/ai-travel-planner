import {
  BedDouble,
  Car,
  CircleDollarSign,
  ShoppingBag,
  Ticket,
  UtensilsCrossed,
  type LucideIcon,
} from "lucide-react"

import type { ExpenseCategory } from "@/api/types"

export interface ExpenseCategoryOption {
  value: ExpenseCategory
  label: string
  icon: LucideIcon
}

/**
 * Mirrors the backend's `ExpenseCategory`. The labels and icons live here
 * because the API validates the value and returns it, but does not send icons.
 */
export const EXPENSE_CATEGORIES: ExpenseCategoryOption[] = [
  { value: "transport", label: "Transport", icon: Car },
  { value: "stay", label: "Stay", icon: BedDouble },
  { value: "food", label: "Food", icon: UtensilsCrossed },
  { value: "activities", label: "Activities", icon: Ticket },
  { value: "shopping", label: "Shopping", icon: ShoppingBag },
  { value: "other", label: "Other", icon: CircleDollarSign },
]

const FALLBACK = EXPENSE_CATEGORIES[EXPENSE_CATEGORIES.length - 1]

export function categoryOption(value: ExpenseCategory): ExpenseCategoryOption {
  return (
    EXPENSE_CATEGORIES.find((option) => option.value === value) ?? FALLBACK
  )
}
