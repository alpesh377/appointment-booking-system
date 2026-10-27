"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";

import { AppointmentCard } from "@/components/appointment-card";
import { ErrorState, Loading, NoItems } from "@/components/page-state";
import { RequireRole } from "@/components/require-role";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, errorMessage } from "@/lib/api";
import type { Appointment } from "@/lib/types";

const VIEWS = [
  { key: "upcoming", label: "Upcoming" },
  { key: "past", label: "Past" },
  { key: "cancelled", label: "Cancelled" },
] as const;

const STATUSES = [
  "PENDING",
  "CONFIRMED",
  "REJECTED",
  "CANCELLED",
  "COMPLETED",
  "EXPIRED",
  "RESCHEDULED",
] as const;

function CustomerDashboard() {
  const [view, setView] = React.useState<(typeof VIEWS)[number]["key"]>("upcoming");
  const [status, setStatus] = React.useState("");
  const [dateFrom, setDateFrom] = React.useState("");
  const [dateTo, setDateTo] = React.useState("");

  const params = new URLSearchParams({ view });
  if (status) params.set("status", status);
  if (dateFrom) params.set("date_from", dateFrom);
  if (dateTo) params.set("date_to", dateTo);

  const appointments = useQuery({
    queryKey: ["appointments", "customer", view, status, dateFrom, dateTo],
    queryFn: () => api.get<Appointment[]>(`/api/appointments?${params.toString()}`),
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">My appointments</h1>
          <p className="text-muted-foreground">
            Times are shown in each provider&apos;s timezone. Cancel or reschedule while more than two
            hours remain.
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Appointment views">
        {VIEWS.map((item) => (
          <Button
            key={item.key}
            role="tab"
            aria-selected={view === item.key}
            variant={view === item.key ? "default" : "outline"}
            size="sm"
            onClick={() => setView(item.key)}
          >
            {item.label}
          </Button>
        ))}
      </div>

      <Card>
        <CardContent className="grid gap-3 pt-6 sm:grid-cols-3">
          <div className="space-y-1">
            <Label htmlFor="status-filter">Status</Label>
            <Select id="status-filter" value={status} onChange={(event) => setStatus(event.target.value)}>
              <option value="">Any status</option>
              {STATUSES.map((item) => (
                <option key={item} value={item}>
                  {item.charAt(0) + item.slice(1).toLowerCase()}
                </option>
              ))}
            </Select>
          </div>
          <div className="space-y-1">
            <Label htmlFor="date-from">From date</Label>
            <Input
              id="date-from"
              type="date"
              value={dateFrom}
              onChange={(event) => setDateFrom(event.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="date-to">To date</Label>
            <Input
              id="date-to"
              type="date"
              value={dateTo}
              onChange={(event) => setDateTo(event.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      {appointments.isPending ? <Loading label="Loading appointments…" /> : null}
      {appointments.isError ? (
        <ErrorState
          message={errorMessage(appointments.error)}
          retry={() => void appointments.refetch()}
        />
      ) : null}
      {appointments.data && appointments.data.length === 0 ? (
        <NoItems
          title={`No ${view} appointments`}
          description={
            view === "upcoming"
              ? "Book a provider from the provider directory to see it here."
              : "Nothing matches the selected filters."
          }
        />
      ) : null}
      {appointments.data && appointments.data.length > 0 ? (
        <div className="grid gap-3">
          {appointments.data.map((appointment) => (
            <AppointmentCard key={appointment.id} appointment={appointment} audience="customer" />
          ))}
        </div>
      ) : null}
    </div>
  );
}

export default function DashboardPage() {
  return (
    <RequireRole roles={["CUSTOMER"]}>
      <CustomerDashboard />
    </RequireRole>
  );
}
