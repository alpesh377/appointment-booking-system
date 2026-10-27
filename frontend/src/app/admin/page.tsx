"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { ErrorState } from "@/components/page-state";
import { RequireRole } from "@/components/require-role";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { api, errorMessage } from "@/lib/api";
import type { AdminStats } from "@/lib/types";

const STATUSES = [
  "PENDING",
  "CONFIRMED",
  "REJECTED",
  "CANCELLED",
  "COMPLETED",
  "EXPIRED",
  "RESCHEDULED",
] as const;

function AdminOverview() {
  const stats = useQuery({
    queryKey: ["admin", "stats"],
    queryFn: () => api.get<AdminStats>("/api/admin/stats"),
  });

  if (stats.isPending) {
    return (
      <div className="space-y-8" role="status" aria-label="Loading platform totals…">
        <Skeleton className="h-8 w-56" />
        <div className="grid gap-4 sm:grid-cols-3">
          {[0, 1, 2].map((card) => (
            <Skeleton key={card} className="h-28 w-full rounded-xl" />
          ))}
        </div>
        <Skeleton className="h-64 w-full rounded-xl" />
      </div>
    );
  }
  if (stats.isError) {
    return <ErrorState message={errorMessage(stats.error)} retry={() => void stats.refetch()} />;
  }

  const data = stats.data;
  const cards = [
    { label: "Customers", value: data.customers },
    { label: "Service providers", value: data.providers },
    { label: "Appointments", value: data.appointments },
  ];

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Administration</h1>
          <p className="text-muted-foreground">
            Platform totals, account management and every appointment in one place.
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/admin/users"
            className="inline-flex h-9 items-center rounded-md border px-3 text-sm font-medium hover:bg-accent"
          >
            Manage users
          </Link>
          <Link
            href="/admin/appointments"
            className="inline-flex h-9 items-center rounded-md border px-3 text-sm font-medium hover:bg-accent"
          >
            All appointments
          </Link>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {cards.map((card) => (
          <Card key={card.label}>
            <CardHeader className="pb-2">
              <CardDescription>{card.label}</CardDescription>
              <CardTitle className="text-3xl">{card.value}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">Includes deactivated records.</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Appointments by status</CardTitle>
          <CardDescription>Distribution across all appointments ever created.</CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="divide-y">
            {STATUSES.map((status) => (
              <li key={status} className="flex items-center justify-between py-2">
                <StatusBadge status={status} />
                <span className="font-medium tabular-nums">{data.by_status[status] ?? 0}</span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}

export default function AdminPage() {
  return (
    <RequireRole roles={["ADMIN"]}>
      <AdminOverview />
    </RequireRole>
  );
}
