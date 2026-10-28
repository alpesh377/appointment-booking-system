"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

import { AppointmentActions } from "@/components/appointment-actions";
import { FadeIn, StatusBadge } from "@/components/motion";
import { ErrorState, Loading } from "@/components/page-state";
import { useAuth } from "@/components/providers";
import { ReschedulePanel } from "@/components/reschedule-panel";
import { Alert } from "@/components/ui/alert";
import { StatusBadge as StaticStatusBadge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiError, errorMessage } from "@/lib/api";
import { formatInstant, formatTime } from "@/lib/format";
import type { Appointment } from "@/lib/types";

function Detail() {
  const params = useParams<{ id: string }>();
  const search = useSearchParams();
  const { user } = useAuth();
  const created = search.get("created") === "1";

  const appointment = useQuery({
    queryKey: ["appointment", params.id],
    queryFn: () => api.get<Appointment>(`/api/appointments/${params.id}`),
    retry: false,
  });

  if (appointment.isPending) {
    return (
      <div className="mx-auto max-w-3xl space-y-6" role="status" aria-label="Loading appointment…">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-40 w-full rounded-xl" />
        <Skeleton className="h-24 w-full rounded-xl" />
        <Skeleton className="h-48 w-full rounded-xl" />
      </div>
    );
  }
  if (appointment.isError) {
    return (
      <ErrorState
        message={
          appointment.error instanceof ApiError && appointment.error.status === 403
            ? "You do not have access to this appointment."
            : errorMessage(appointment.error)
        }
      />
    );
  }

  const data = appointment.data;
  const timeZone = data.provider.timezone;
  const now = Date.now();
  const canReschedule =
    user?.role === "CUSTOMER" &&
    (data.status === "PENDING" || data.status === "CONFIRMED") &&
    new Date(data.starts_at).getTime() - now > 2 * 60 * 60 * 1000;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {created ? (
        <FadeIn>
          <Alert variant="success" title="Appointment requested">
            The provider will confirm or reject it; the slot is held while it is pending.
          </Alert>
        </FadeIn>
      ) : null}

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Appointment</h1>
          <p className="text-muted-foreground">
            {data.service.name} with {data.provider.display_name}
          </p>
        </div>
        <StatusBadge statusKey={data.status}>
          <StaticStatusBadge status={data.status} />
        </StatusBadge>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <p className="text-muted-foreground">Starts</p>
              <p className="font-medium">{formatInstant(data.starts_at, timeZone)}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Ends</p>
              <p className="font-medium">{formatInstant(data.ends_at, timeZone)}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Duration</p>
              <p className="font-medium">{data.duration_minutes} minutes</p>
            </div>
            <div>
              <p className="text-muted-foreground">Timezone</p>
              <p className="font-medium">{timeZone}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Customer</p>
              <p className="font-medium">{data.customer.full_name}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Provider</p>
              <p className="font-medium">{data.provider.display_name}</p>
            </div>
          </div>
          <Separator />
          <div>
            <p className="text-muted-foreground">Notes</p>
            <p>{data.notes ?? "No notes were added."}</p>
          </div>
          {data.cancelled_by_role ? (
            <>
              <Separator />
              <div>
                <p className="text-muted-foreground">Cancelled by</p>
                <p>
                  {data.cancelled_by_role}
                  {data.cancellation_reason ? ` — ${data.cancellation_reason}` : ""}
                </p>
              </div>
            </>
          ) : null}
          {data.rescheduled_from_id || data.rescheduled_to_id ? (
            <>
              <Separator />
              <div className="flex flex-wrap gap-4">
                {data.rescheduled_from_id ? (
                  <Link
                    href={`/appointments/${data.rescheduled_from_id}`}
                    className={buttonVariants({ variant: "link", className: "h-auto p-0 text-sm" })}
                  >
                    Rescheduled from an earlier appointment
                  </Link>
                ) : null}
                {data.rescheduled_to_id ? (
                  <Link
                    href={`/appointments/${data.rescheduled_to_id}`}
                    className={buttonVariants({ variant: "link", className: "h-auto p-0 text-sm" })}
                  >
                    Rescheduled to a new appointment
                  </Link>
                ) : null}
              </div>
            </>
          ) : null}
        </CardContent>
      </Card>

      {user ? (
        <Card>
          <CardHeader>
            <CardTitle>Actions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <AppointmentActions appointment={data} role={user.role} />
            {data.hold_expires_at ? (
              <p className="text-sm text-muted-foreground">
                This request is held until {formatInstant(data.hold_expires_at, timeZone)}.
              </p>
            ) : null}
          </CardContent>
        </Card>
      ) : null}

      {canReschedule ? <ReschedulePanel appointment={data} /> : null}

      <Card>
        <CardHeader>
          <CardTitle>History</CardTitle>
        </CardHeader>
        <CardContent>
          <ol className="space-y-3">
            {(data.events ?? []).map((event) => (
              <li key={event.id} className="border-l-2 pl-3">
                <p className="text-sm font-medium">
                  {event.from_status ? `${event.from_status} → ` : ""}
                  {event.to_status}
                </p>
                <p className="text-sm text-muted-foreground">
                  {formatTime(event.created_at, timeZone)} · {event.actor_role.toLowerCase()}
                  {event.reason ? ` · ${event.reason}` : ""}
                </p>
              </li>
            ))}
            {(data.events ?? []).length === 0 ? (
              <li className="text-sm text-muted-foreground">No transitions recorded yet.</li>
            ) : null}
          </ol>
        </CardContent>
      </Card>
    </div>
  );
}

export default function AppointmentDetailPage() {
  return (
    <React.Suspense fallback={<Loading label="Loading appointment…" />}>
      <Detail />
    </React.Suspense>
  );
}
