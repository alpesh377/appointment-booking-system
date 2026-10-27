"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Loader2Icon } from "lucide-react";

import {
  Pressable,
  SelectionHighlight,
  Swap,
} from "@/components/motion";
import { ErrorState, Loading } from "@/components/page-state";
import { RequireRole } from "@/components/require-role";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Select, Textarea } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toastError, toastSuccess } from "@/components/ui/toast";
import { api, ApiError, errorMessage } from "@/lib/api";
import { formatDate, formatTime } from "@/lib/format";
import type { Appointment, Provider, SlotResponse } from "@/lib/types";

function isoDate(offsetDays: number): string {
  const date = new Date();
  date.setDate(date.getDate() + offsetDays);
  return date.toISOString().slice(0, 10);
}

/** Which part of the day a slot falls in, in the provider's timezone. */
function partOfDay(iso: string, timeZone: string): "Morning" | "Afternoon" | "Evening" {
  const hour = Number(
    new Intl.DateTimeFormat("en-GB", { hour: "2-digit", hour12: false, timeZone }).format(
      new Date(iso),
    ),
  );
  if (hour >= 17) return "Evening";
  if (hour >= 12) return "Afternoon";
  return "Morning";
}

const PARTS = ["Morning", "Afternoon", "Evening"] as const;

function BookingForm() {
  const params = useParams<{ id: string }>();
  const search = useSearchParams();
  const router = useRouter();
  const [serviceId, setServiceId] = React.useState(search.get("service") ?? "");
  const [date, setDate] = React.useState(isoDate(1));
  const [slot, setSlot] = React.useState<string | null>(null);
  const [notes, setNotes] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = React.useState<Record<string, string>>({});

  const provider = useQuery({
    queryKey: ["provider", params.id],
    queryFn: () => api.get<Provider>(`/api/providers/${params.id}`),
    retry: false,
  });

  React.useEffect(() => {
    if (!serviceId && provider.data && provider.data.services.length > 0) {
      setServiceId(provider.data.services[0].id);
    }
  }, [provider.data, serviceId]);

  const slots = useQuery({
    queryKey: ["availability", params.id, serviceId, date],
    queryFn: () =>
      api.get<SlotResponse>(
        `/api/availability?provider_id=${params.id}&service_id=${serviceId}` +
          `&date_from=${date}&date_to=${date}`,
      ),
    enabled: Boolean(serviceId),
  });

  const grouped = React.useMemo(() => {
    const timeZoneForSlots =
      (provider.data?.timezone as string | undefined) ?? "UTC";
    const groups = new Map<(typeof PARTS)[number], string[]>();
    for (const part of PARTS) groups.set(part, []);
    for (const option of slots.data?.slots ?? []) {
      groups.get(partOfDay(option, timeZoneForSlots))?.push(option);
    }
    return PARTS.map((part) => ({ part, options: groups.get(part) ?? [] }));
  }, [slots.data, provider.data]);
  const hasSlots = grouped.some((group) => group.options.length > 0);

  const booking = useMutation({
    mutationFn: () =>
      api.post<Appointment>("/api/appointments", {
        provider_id: params.id,
        service_id: serviceId,
        starts_at: slot,
        notes: notes.trim() || null,
      }),
    onSuccess: (appointment) => {
      toastSuccess(
        "Appointment requested",
        "You will see it as Pending until the provider responds.",
      );
      router.replace(`/appointments/${appointment.id}?created=1`);
    },
    onError: (caught) => {
      if (caught instanceof ApiError && caught.fields) setFieldErrors(caught.fields);
      setError(errorMessage(caught));
      toastError("Booking could not be completed", errorMessage(caught));
      void slots.refetch();
    },
  });

  if (provider.isPending) return <Loading label="Loading provider…" />;
  if (provider.isError) return <ErrorState message={errorMessage(provider.error)} />;

  const data = provider.data;
  const timeZone = data.timezone;
  const selectedService = data.services.find((service) => service.id === serviceId);

  const summaryRow = (label: string, value: React.ReactNode) => (
    <div className="flex items-baseline justify-between gap-3 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-right font-medium">{value ?? "—"}</span>
    </div>
  );

  return (
    <div className="mx-auto max-w-5xl">
      <div>
        <Link
          href={`/providers/${data.id}`}
          className="text-sm font-medium text-primary underline-offset-4 hover:underline"
        >
          ← Back to {data.display_name}
        </Link>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight">Book with {data.display_name}</h1>
        <p className="text-muted-foreground">All times are shown in {timeZone}.</p>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_300px] lg:items-start">
        <Card>
          <CardHeader>
            <CardTitle>Choose a service, date and time</CardTitle>
            <CardDescription>
              The duration comes from the service. The slot is reserved while a request is pending.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1">
                <Label htmlFor="service">Service</Label>
                <Select
                  id="service"
                  value={serviceId}
                  onChange={(event) => {
                    setServiceId(event.target.value);
                    setSlot(null);
                  }}
                >
                  {data.services.length === 0 ? <option value="">No services available</option> : null}
                  {data.services.map((service) => (
                    <option key={service.id} value={service.id}>
                      {service.name} ({service.duration_minutes} min)
                    </option>
                  ))}
                </Select>
                {fieldErrors.service_id ? (
                  <p className="text-sm text-destructive">{fieldErrors.service_id}</p>
                ) : null}
              </div>
              <div className="space-y-1">
                <Label htmlFor="date">Date</Label>
                <Input
                  id="date"
                  type="date"
                  value={date}
                  min={isoDate(0)}
                  max={isoDate(30)}
                  onChange={(event) => {
                    setDate(event.target.value);
                    setSlot(null);
                  }}
                />
                {fieldErrors.date ? <p className="text-sm text-destructive">{fieldErrors.date}</p> : null}
              </div>
            </div>

            <div className="space-y-3">
              <p className="text-sm font-medium">Available times</p>
              {!serviceId ? (
                <Alert variant="muted" title="Choose a service to see available times" />
              ) : slots.isPending ? (
                <div
                  role="status"
                  aria-label="Loading available times"
                  className="flex flex-wrap gap-2"
                  aria-hidden
                >
                  {Array.from({ length: 6 }).map((_, index) => (
                    <div key={index} className="h-8 w-24 animate-pulse rounded-md bg-accent" />
                  ))}
                </div>
              ) : slots.isError ? (
                <ErrorState message={errorMessage(slots.error)} retry={() => void slots.refetch()} />
              ) : slots.data && slots.data.slots.length === 0 ? (
                <Alert variant="muted" title="No times are available on this date">
                  Try another date — times are offered in {timeZone} within the next 30 days.
                </Alert>
              ) : (
                <Swap swapKey={`${serviceId}|${date}`}>
                  <div className="space-y-4">
                    {hasSlots
                      ? grouped
                          .filter((group) => group.options.length > 0)
                          .map((group) => (
                            <div key={group.part} className="space-y-2">
                              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                                {group.part}
                              </p>
                              <div className="flex flex-wrap gap-2">
                                {group.options.map((option) => {
                                  const selected = slot === option;
                                  return (
                                    <Pressable key={option} className="relative">
                                      <button
                                        type="button"
                                        aria-pressed={selected}
                                        onClick={() => setSlot(option)}
                                        className="relative inline-flex h-9 items-center justify-center rounded-md border border-input bg-background px-3 text-sm font-medium hover:bg-accent hover:text-accent-foreground focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                                      >
                                        {selected ? (
                                          <SelectionHighlight
                                            layoutId="booking-slot-selection"
                                            className="absolute inset-0 rounded-md bg-primary"
                                          />
                                        ) : null}
                                        <span
                                          className={
                                            selected ? "relative z-10 text-primary-foreground" : "relative z-10"
                                          }
                                        >
                                          {formatTime(option, timeZone)}
                                        </span>
                                      </button>
                                    </Pressable>
                                  );
                                })}
                              </div>
                            </div>
                          ))
                      : null}
                  </div>
                </Swap>
              )}
            </div>

            <div className="space-y-1">
              <Label htmlFor="notes">Notes (optional)</Label>
              <Textarea
                id="notes"
                value={notes}
                maxLength={2000}
                onChange={(event) => setNotes(event.target.value)}
                placeholder="Anything the provider should know"
              />
              {fieldErrors.notes ? <p className="text-sm text-destructive">{fieldErrors.notes}</p> : null}
            </div>

            {error ? (
              <Alert variant="error" title="Booking could not be completed">
                {error}
                {error.toLowerCase().includes("no longer available") ? (
                  <button
                    type="button"
                    className="mt-2 block text-sm font-medium underline"
                    onClick={() => void slots.refetch()}
                  >
                    Refresh availability
                  </button>
                ) : null}
              </Alert>
            ) : null}
          </CardContent>
        </Card>

        <Card className="lg:sticky lg:top-6">
          <CardHeader>
            <CardTitle className="text-base">Your request</CardTitle>
            <CardDescription>Confirm the details before submitting.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {summaryRow("Provider", data.display_name)}
            {summaryRow(
              "Service",
              selectedService ? (
                <>
                  {selectedService.name}
                  <span className="text-muted-foreground"> · {selectedService.duration_minutes} min</span>
                </>
              ) : null,
            )}
            {summaryRow("Date", date ? formatDate(`${date}T12:00:00Z`, timeZone) : null)}
            {summaryRow("Time", slot ? formatTime(slot, timeZone) : null)}
            <div className="pt-2">
              <Button
                type="button"
                className="w-full"
                disabled={!slot || !selectedService || booking.isPending}
                onClick={() => {
                  setError(null);
                  setFieldErrors({});
                  booking.mutate();
                }}
              >
                {booking.isPending ? (
                  <>
                    <Loader2Icon aria-hidden className="size-4 animate-spin" />
                    Requesting…
                  </>
                ) : (
                  "Request appointment"
                )}
              </Button>
              <p className="mt-2 text-center text-xs text-muted-foreground">
                {slot ? "The slot stays reserved while the provider responds." : "Pick a time to continue."}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default function BookingPage() {
  return (
    <RequireRole roles={["CUSTOMER"]}>
      <React.Suspense fallback={<Loading label="Loading booking form…" />}>
        <BookingForm />
      </React.Suspense>
    </RequireRole>
  );
}
