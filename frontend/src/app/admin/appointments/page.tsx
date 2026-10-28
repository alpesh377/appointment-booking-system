"use client";

import * as React from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { DateFilter } from "@/components/date-filter";
import { ErrorState, NoItems } from "@/components/page-state";
import { RequireRole } from "@/components/require-role";
import { Alert } from "@/components/ui/alert";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { toastError, toastSuccess } from "@/components/ui/toast";
import { api, errorMessage } from "@/lib/api";
import { formatInstant } from "@/lib/format";
import type { AdminAppointments, Appointment, Provider, User } from "@/lib/types";

const STATUSES = [
  "PENDING",
  "CONFIRMED",
  "REJECTED",
  "CANCELLED",
  "COMPLETED",
  "EXPIRED",
  "RESCHEDULED",
] as const;

const PAGE_SIZE = 20;

function AdminAppointments() {
  const queryClient = useQueryClient();
  const [status, setStatus] = React.useState("");
  const [providerId, setProviderId] = React.useState("");
  const [customerId, setCustomerId] = React.useState("");
  const [dateFrom, setDateFrom] = React.useState("");
  const [dateTo, setDateTo] = React.useState("");
  const [page, setPage] = React.useState(1);
  const [error, setError] = React.useState<string | null>(null);

  const providers = useQuery({
    queryKey: ["admin", "providers"],
    queryFn: () => api.get<Provider[]>("/api/admin/providers"),
  });
  const customers = useQuery({
    queryKey: ["admin", "customers", ""],
    queryFn: () => api.get<User[]>("/api/admin/customers"),
  });

  const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
  if (status) params.set("status", status);
  if (providerId) params.set("provider_id", providerId);
  if (customerId) params.set("customer_id", customerId);
  if (dateFrom) params.set("date_from", dateFrom);
  if (dateTo) params.set("date_to", dateTo);

  const appointments = useQuery({
    queryKey: ["admin", "appointments", status, providerId, customerId, dateFrom, dateTo, page],
    queryFn: () => api.get<AdminAppointments>(`/api/admin/appointments?${params.toString()}`),
  });

  const cancel = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      api.post<Appointment>(`/api/admin/appointments/${id}/cancel`, { reason: reason || null }),
    // Optimistic: the row disappears from the list immediately and is
    // restored verbatim when the cancel fails.
    onMutate: async ({ id }) => {
      await queryClient.cancelQueries({ queryKey: ["admin", "appointments"] });
      const previous = queryClient.getQueryData<AdminAppointments>(["admin", "appointments", "", providerId, customerId, dateFrom, dateTo, page]);
      const next = previous
        ? {
            ...previous,
            items: previous.items.filter((appointment) => appointment.id !== id),
            total: Math.max(0, previous.total - 1),
          }
        : undefined;
      if (next) {
        queryClient.setQueryData<AdminAppointments>(
          ["admin", "appointments", "", providerId, customerId, dateFrom, dateTo, page],
          next,
        );
      }
      return { previous };
    },
    onSuccess: () => {
      setError(null);
      toastSuccess("Appointment cancelled", "The supervisory cancellation is recorded.");
      void queryClient.invalidateQueries();
    },
    onError: (caught, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(
          ["admin", "appointments", "", providerId, customerId, dateFrom, dateTo, page],
          context.previous,
        );
      }
      const message = errorMessage(caught);
      setError(message);
      toastError("Could not cancel the appointment", message);
    },
  });

  const totalPages = appointments.data
    ? Math.max(1, Math.ceil(appointments.data.total / PAGE_SIZE))
    : 1;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">All appointments</h1>
        <p className="text-muted-foreground">
          Every appointment, including those belonging to deactivated accounts. Administrators may
          cancel only; confirmation, rejection, completion and rescheduling stay with the provider or
          customer.
        </p>
      </div>

      {error ? <Alert variant="error" title="Action failed">{error}</Alert> : null}

      <Card>
        <CardContent className="grid gap-3 pt-6 sm:grid-cols-2 lg:grid-cols-5">
          <div className="space-y-1">
            <Label htmlFor="admin-status">Status</Label>
            <Select
              value={status || "all"}
              onValueChange={(value) => {
                setStatus(value === "all" ? "" : value);
                setPage(1);
              }}
            >
              <SelectTrigger id="admin-status" className="h-10 w-full">
                <SelectValue placeholder="Any status" />
              </SelectTrigger>
              <SelectContent position="popper" align="start">
                <SelectItem value="all">Any status</SelectItem>
                {STATUSES.map((item) => (
                  <SelectItem key={item} value={item}>
                    {item.charAt(0) + item.slice(1).toLowerCase()}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label htmlFor="admin-provider">Provider</Label>
            <Select
              value={providerId || "all"}
              onValueChange={(value) => {
                setProviderId(value === "all" ? "" : value);
                setPage(1);
              }}
            >
              <SelectTrigger id="admin-provider" className="h-10 w-full">
                <SelectValue placeholder="Any provider" />
              </SelectTrigger>
              <SelectContent position="popper" align="start">
                <SelectItem value="all">Any provider</SelectItem>
                {providers.data?.map((provider) => (
                  <SelectItem key={provider.id} value={provider.id}>
                    {provider.display_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label htmlFor="admin-customer">Customer</Label>
            <Select
              value={customerId || "all"}
              onValueChange={(value) => {
                setCustomerId(value === "all" ? "" : value);
                setPage(1);
              }}
            >
              <SelectTrigger id="admin-customer" className="h-10 w-full">
                <SelectValue placeholder="Any customer" />
              </SelectTrigger>
              <SelectContent position="popper" align="start">
                <SelectItem value="all">Any customer</SelectItem>
                {customers.data?.map((customer) => (
                  <SelectItem key={customer.id} value={customer.id}>
                    {customer.full_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <DateFilter
            id="admin-from"
            label="From"
            value={dateFrom}
            onChange={(value) => {
              setDateFrom(value);
              setPage(1);
            }}
          />
          <DateFilter
            id="admin-to"
            label="To"
            value={dateTo}
            onChange={(value) => {
              setDateTo(value);
              setPage(1);
            }}
          />
        </CardContent>
      </Card>

      {appointments.isPending ? (
        <div className="space-y-3" role="status" aria-label="Loading appointments…">
          {[0, 1, 2, 3].map((row) => (
            <Skeleton key={row} className="h-16 w-full rounded-lg" />
          ))}
        </div>
      ) : null}
      {appointments.isError ? (
        <ErrorState
          message={errorMessage(appointments.error)}
          retry={() => void appointments.refetch()}
        />
      ) : null}
      {appointments.data && appointments.data.items.length === 0 ? (
        <NoItems title="No appointments match these filters" />
      ) : null}

      {appointments.data && appointments.data.items.length > 0 ? (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            {appointments.data.total} appointment(s) · page {appointments.data.page} of {totalPages}
          </p>
          <ul className="divide-y rounded-lg border">
            {appointments.data.items.map((appointment) => {
              const cancellable =
                appointment.status === "PENDING" || appointment.status === "CONFIRMED";
              return (
                <li key={appointment.id} className="flex flex-wrap items-center justify-between gap-3 p-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <StatusBadge status={appointment.status} />
                      <Link
                        href={`/appointments/${appointment.id}`}
                        className="truncate font-medium underline-offset-4 hover:underline"
                      >
                        {appointment.customer.full_name} · {appointment.provider.display_name}
                      </Link>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {appointment.service.name} ·{" "}
                      {formatInstant(appointment.starts_at, appointment.provider.timezone)}
                    </p>
                  </div>
                  {cancellable ? (
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={cancel.isPending}
                      onClick={() => {
                        const reason = window.prompt("Reason for cancellation (optional)") ?? "";
                        cancel.mutate({ id: appointment.id, reason });
                      }}
                    >
                      Cancel appointment
                    </Button>
                  ) : null}
                </li>
              );
            })}
          </ul>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              disabled={page <= 1}
              onClick={() => setPage((current) => Math.max(1, current - 1))}
            >
              Previous
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={page >= totalPages}
              onClick={() => setPage((current) => current + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default function AdminAppointmentsPage() {
  return (
    <RequireRole roles={["ADMIN"]}>
      <AdminAppointments />
    </RequireRole>
  );
}
