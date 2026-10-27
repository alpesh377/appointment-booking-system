import type { FieldValues, Path, UseFormSetError } from "react-hook-form";

import { ApiError } from "@/lib/api";

/** Copy FastAPI per-field validation messages onto the matching form fields. */
export function applyApiFieldErrors<T extends FieldValues>(
  setError: UseFormSetError<T>,
  error: unknown,
): boolean {
  if (!(error instanceof ApiError) || !error.fields) return false;
  let applied = false;
  for (const [field, message] of Object.entries(error.fields)) {
    setError(field as Path<T>, { type: "server", message });
    applied = true;
  }
  return applied;
}
