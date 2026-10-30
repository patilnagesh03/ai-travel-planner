import {
  differenceInCalendarDays,
  eachDayOfInterval,
  format,
  isValid,
  parseISO,
} from "date-fns"

export function formatDate(value: string): string {
  const date = parseISO(value)

  return isValid(date) ? format(date, "d MMM yyyy") : value
}

export function formatDateShort(value: string): string {
  const date = parseISO(value)

  return isValid(date) ? format(date, "d MMM") : value
}

export function formatWeekday(value: string): string {
  const date = parseISO(value)

  return isValid(date) ? format(date, "EEEE") : value
}

export function formatWeekdayShort(value: string): string {
  const date = parseISO(value)

  return isValid(date) ? format(date, "EEE") : value
}

export function formatDateRange(start: string, end: string): string {
  const startDate = parseISO(start)
  const endDate = parseISO(end)

  if (!isValid(startDate) || !isValid(endDate)) {
    return `${start} – ${end}`
  }

  if (startDate.getFullYear() === endDate.getFullYear()) {
    return `${format(startDate, "d MMM")} – ${format(endDate, "d MMM yyyy")}`
  }

  return `${format(startDate, "d MMM yyyy")} – ${format(endDate, "d MMM yyyy")}`
}

export function tripNightCount(start: string, end: string): number {
  const startDate = parseISO(start)
  const endDate = parseISO(end)

  if (!isValid(startDate) || !isValid(endDate)) {
    return 0
  }

  return Math.max(0, differenceInCalendarDays(endDate, startDate))
}

export function tripDayCount(start: string, end: string): number {
  return tripNightCount(start, end) + 1
}

export function enumerateDates(start: string, end: string): string[] {
  const startDate = parseISO(start)
  const endDate = parseISO(end)

  if (!isValid(startDate) || !isValid(endDate) || endDate < startDate) {
    return []
  }

  return eachDayOfInterval({ start: startDate, end: endDate }).map((date) =>
    format(date, "yyyy-MM-dd"),
  )
}

export function formatCurrency(amount: string | number, currency = "INR"): string {
  const numericAmount = typeof amount === "number" ? amount : Number(amount)

  if (!Number.isFinite(numericAmount)) {
    return `${currency} ${amount}`
  }

  try {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency,
      maximumFractionDigits: 0,
    }).format(numericAmount)
  } catch {
    return `${currency} ${numericAmount.toLocaleString("en-IN")}`
  }
}

export function formatTime(value: string | null): string {
  if (!value) {
    return ""
  }

  const [hoursPart, minutesPart] = value.split(":")
  const hours = Number(hoursPart)
  const minutes = Number(minutesPart)

  if (!Number.isFinite(hours) || !Number.isFinite(minutes)) {
    return value
  }

  const date = new Date()
  date.setHours(hours, minutes, 0, 0)

  return format(date, "h:mm a")
}

export function formatTimeRange(
  start: string | null,
  end: string | null,
): string {
  if (start && end) {
    return `${formatTime(start)} – ${formatTime(end)}`
  }

  return formatTime(start) || formatTime(end)
}

export function titleCase(value: string): string {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase())
}

export function initials(firstName: string, lastName: string): string {
  return `${firstName.charAt(0)}${lastName.charAt(0)}`.toUpperCase()
}

export function currentDateInputValue(): string {
  return format(new Date(), "yyyy-MM-dd")
}
