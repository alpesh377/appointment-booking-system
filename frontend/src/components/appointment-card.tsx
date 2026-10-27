import Link from "next/link";

import { StatusBadge } from "@/components/ui/badge";
import { formatDate, formatTime } from "@/lib/format";
import type { Appointment } from "@/lib/types";

export function AppointmentCard({
  appointment,
  audience = "customer",
}: {
  appointment: Appointment;
  audience?: "customer" | "provider" | "admin";
}) {
  const timeZone = appointment.provider.timezone;
  return (
    <Link
      href={`/appointments/${appointment.id}`}
      className="block rounded-lg border bg-card p-4 shadow-xs transition-colors hover:bg-accent/40"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate font-medium">
            {audience === "customer" ? appointment.provider.display_name : appointment.customer.full_name}
          </p>
          <p className="truncate text-sm text-muted-foreground">
            {appointment.service.name} · {appointment.duration_minutes} min
          </p>
        </div>
        <StatusBadge status={appointment.status} />
      </div>
      <p className="mt-2 text-sm">
        {formatDate(appointment.starts_at, timeZone)} · {formatTime(appointment.starts_at, timeZone)} –{" "}
        {formatTime(appointment.ends_at, timeZone)}
      </p>
      <p className="mt-1 text-xs text-muted-foreground">Times shown in {timeZone}</p>
    </Link>
  );
}
