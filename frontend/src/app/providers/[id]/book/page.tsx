"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";

import { ErrorState, Loading } from "@/components/page-state";
import { RequireRole } from "@/components/require-role";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Select, Textarea } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError, errorMessage } from "@/lib/api";
import { formatTime } from "@/lib/format";
import type { Appointment, Provider, SlotResponse } from "@/lib/types";

function isoDate(offsetDays: number): string {
  const date = new Date();
  date.setDate(date.getDate() + offsetDays);
  return date.toISOString().slice(0, 10);
}

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

  const booking = useMutation({
    mutationFn: () =>
      api.post<Appointment>("/api/appointments", {
        provider_id: params.id,
        service_id: serviceId,
        starts_at: slot,
        notes: notes.trim() || null,
      }),
    onSuccess: (appointment) => router.replace(`/appointments/${appointment.id}?created=1`),
    onError: (caught) => {
      if (caught instanceof ApiError && caught.fields) setFieldErrors(caught.fields);
      setError(errorMessage(caught));
      void slots.refetch();
    },
  });

  if (provider.isPending) return <Loading label="Loading provider…" />;
  if (provider.isError) return <ErrorState message={errorMessage(provider.error)} />;

  const data = provider.data;
  const timeZone = data.timezone;
  const selectedService = data.services.find((service) => service.id === serviceId);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
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

          <div className="space-y-2">
            <p className="text-sm font-medium">Available times</p>
            {!serviceId ? (
              <Alert variant="muted" title="Choose a service to see available times" />
            ) : slots.isPending ? (
              <Loading label="Loading available times…" />
            ) : slots.isError ? (
              <ErrorState message={errorMessage(slots.error)} retry={() => void slots.refetch()} />
            ) : slots.data && slots.data.slots.length === 0 ? (
              <Alert variant="muted" title="No times are available on this date">
                Try another date — times are offered in {timeZone} within the next 30 days.
              </Alert>
            ) : (
              <div className="flex flex-wrap gap-2">
                {slots.data?.slots.map((option) => (
                  <Button
                    key={option}
                    type="button"
                    size="sm"
                    variant={slot === option ? "default" : "outline"}
                    onClick={() => setSlot(option)}
                  >
                    {formatTime(option, timeZone)}
                  </Button>
                ))}
              </div>
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

          <div className="flex flex-wrap items-center gap-3">
            <Button
              type="button"
              disabled={!slot || !selectedService || booking.isPending}
              onClick={() => {
                setError(null);
                setFieldErrors({});
                booking.mutate();
              }}
            >
              {booking.isPending ? "Requesting…" : "Request appointment"}
            </Button>
            <p className="text-sm text-muted-foreground">
              {selectedService ? `${selectedService.duration_minutes} minutes` : "Select a service"}
              {slot ? ` · ${formatTime(slot, timeZone)}` : ""}
            </p>
          </div>
        </CardContent>
      </Card>
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
