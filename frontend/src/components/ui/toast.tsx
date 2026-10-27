"use client"

import { toast } from "sonner"

/**
 * Shared toast API so every page acknowledges success and names failure the
 * same way. Durations are short on purpose — they are confirmations, not logs.
 */
export function toastSuccess(message: string, description?: string) {
  toast.success(message, { description, duration: 4000 })
}

export function toastError(message: string, description?: string) {
  toast.error(message, { description, duration: 6000 })
}

export { toast }
