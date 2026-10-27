"use client";

import * as React from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { AppointmentCard } from "@/components/appointment-card";
import { ErrorState, Loading, NoItems } from "@/components/page-state";
import { RequireRole } from "@/components/require-role";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, errorMessage } from "@/lib/api";
import type { Appointment, ProviderDashboard } from "@/lib/types";

type Transition = "confirm" | "reject" | "complete";

function ProviderHome() {
  const queryClient = useQueryClient();
  const [error, setError] = React.useState<string | null>(null);

  const dashboard = useQuery({
    queryKey: ["dashboard", "provider"],
    queryFn: () => api.get<ProviderDashboard>("/api/dashboard/provider"),
  });

  const transition = useMutation({
    mutationFn: ({ id, action }: { id: string; action: Transition }) =>
      api.post<Appointment>(`/api/appointments/${id}/${action}`, { reason: null }),
    onSuccess: () => {
      setError(null);
      void queryClient.invalidateQueries();
    },
    onError: (caught) => setError(errorMessage(caught)),
  });

  if (dashboard.isPending) return <Loading label="Loading your dashboard…" />;
  if (dashboard.isError) {
    return (
      <ErrorState
        message={errorMessage(dashboard.error)}
        retry={() => void dashboard.refetch()}
      />
    );
  }

  const data = dashboard.data;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Provider dashboard</h1>
          <p className="text-muted-foreground">
            Today and all times are shown in your practice timezone.
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/provider/availability"
            className="inline-flex h-9 items-center rounded-md border px-3 text-sm font-medium hover:bg-accent"
          >
            Availability
          </Link>
          <Link
            href="/provider/services"
            className="inline-flex h-9 items-center rounded-md border px-3 text-sm font-medium hover:bg-accent"
          >
            Services
          </Link>
        </div>
      </div>

      {error ? <Alert variant="error" title="Action failed">{error}</Alert> : null}

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Today</h2>
          <span className="text-sm text-muted-foreground">{data.today.length} appointment(s)</span>
        </div>
        {data.today.length === 0 ? (
          <NoItems title="No appointments today" description="Your working day is clear." />
        ) : (
          <div className="grid gap-3">
            {data.today.map((appointment) => (
              <AppointmentCard key={appointment.id} appointment={appointment} audience="provider" />
            ))}
          </div>
        )}
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Pending requests</h2>
          <span className="text-sm text-muted-foreground">{data.pending.length} waiting</span>
        </div>
        {data.pending.length === 0 ? (
          <NoItems title="No pending requests" description="New booking requests appear here." />
        ) : (
          <div className="grid gap-3">
            {data.pending.map((appointment) => (
              <Card key={appointment.id}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">{appointment.customer.full_name}</CardTitle>
                  <CardDescription>
                    {appointment.service.name} ·{" "}
                    {new Date(appointment.starts_at).toLocaleString("en-GB", {
                      timeZone: appointment.provider.timezone,
                      dateStyle: "medium",
                      timeStyle: "short",
                    })}{" "}
                    ({appointment.provider.timezone})
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex flex-wrap items-center gap-2">
                  <Button
                    size="sm"
                    disabled={transition.isPending}
                    onClick={() => transition.mutate({ id: appointment.id, action: "confirm" })}
                  >
                    Confirm
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={transition.isPending}
                    onClick={() => transition.mutate({ id: appointment.id, action: "reject" })}
                  >
                    Reject
                  </Button>
                  <Link
                    href={`/appointments/${appointment.id}`}
                    className="text-sm font-medium text-primary underline-offset-4 hover:underline"
                  >
                    Open details
                  </Link>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Upcoming</h2>
          <span className="text-sm text-muted-foreground">{data.upcoming.length}</span>
        </div>
        {data.upcoming.length === 0 ? (
          <NoItems title="No upcoming appointments" />
        ) : (
          <div className="grid gap-3">
            {data.upcoming.map((appointment) => (
              <AppointmentCard key={appointment.id} appointment={appointment} audience="provider" />
            ))}
          </div>
        )}
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Awaiting completion</h2>
          <span className="text-sm text-muted-foreground">{data.awaiting_completion.length}</span>
        </div>
        <p className="text-sm text-muted-foreground">
          Confirmed appointments whose end time has passed. Completion is never automatic.
        </p>
        {data.awaiting_completion.length === 0 ? (
          <NoItems title="Nothing awaits completion" />
        ) : (
          <div className="grid gap-3">
            {data.awaiting_completion.map((appointment) => (
              <Card key={appointment.id}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">{appointment.customer.full_name}</CardTitle>
                  <CardDescription>
                    {appointment.service.name} ·{" "}
                    {new Date(appointment.starts_at).toLocaleString("en-GB", {
                      timeZone: appointment.provider.timezone,
                      dateStyle: "medium",
                      timeStyle: "short",
                    })}
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex flex-wrap items-center gap-2">
                  <Button
                    size="sm"
                    disabled={transition.isPending}
                    onClick={() => transition.mutate({ id: appointment.id, action: "complete" })}
                  >
                    Mark completed
                  </Button>
                  <Link
                    href={`/appointments/${appointment.id}`}
                    className="text-sm font-medium text-primary underline-offset-4 hover:underline"
                  >
                    Open details
                  </Link>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Appointments outside current availability</h2>
        <p className="text-sm text-muted-foreground">
          These remain unchanged after a schedule edit and need manual handling.
        </p>
        {data.conflicts.length === 0 ? (
          <NoItems title="No conflicts" description="Every active appointment fits your schedule." />
        ) : (
          <div className="grid gap-3">
            {data.conflicts.map((appointment) => (
              <AppointmentCard key={appointment.id} appointment={appointment} audience="provider" />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

export default function ProviderDashboardPage() {
  return (
    <RequireRole roles={["PROVIDER"]}>
      <ProviderHome />
    </RequireRole>
  );
}
