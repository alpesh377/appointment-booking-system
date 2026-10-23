import * as React from "react";

import { cn } from "@/lib/utils";
import { statusLabel } from "@/lib/format";

const variants: Record<string, string> = {
  PENDING: "bg-amber-100 text-amber-800 border-amber-200",
  CONFIRMED: "bg-emerald-100 text-emerald-800 border-emerald-200",
  REJECTED: "bg-rose-100 text-rose-800 border-rose-200",
  CANCELLED: "bg-slate-100 text-slate-700 border-slate-200",
  COMPLETED: "bg-sky-100 text-sky-800 border-sky-200",
  EXPIRED: "bg-zinc-100 text-zinc-700 border-zinc-200",
  RESCHEDULED: "bg-violet-100 text-violet-800 border-violet-200",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold",
        variants[status] ?? "bg-muted text-muted-foreground",
      )}
    >
      {statusLabel(status)}
    </span>
  );
}

export function Badge({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
        className,
      )}
    >
      {children}
    </span>
  );
}
