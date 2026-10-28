"use client";

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ErrorState, Loading } from "@/components/page-state";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { DatePicker } from "@/components/ui/date-picker";
import { Label } from "@/components/ui/label";
import { toastError, toastSuccess } from "@/components/ui/toast";
import { api, errorMessage } from "@/lib/api";
import { formatTime } from "@/lib/format";
import type { Appointment, SlotResponse } from "@/lib/types";

function isoDate(offsetDays: number): string {
  const date = new Date();
  date.setDate(date.getDate() + offsetDays);
  return date.toISOString().slice(0, 10);
}

export function ReschedulePanel({ appointment }: { appointment: Appointment }) {
  const [date, setDate] = React.useState(isoDate(1));
  const [selected, setSelected] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const queryClient = useQueryClient();
  const timeZone = appointment.provider.timezone;

  const slots = useQuery({
    queryKey: ["availability", appointment.provider.id, appointment.service.id, date],
    queryFn: () =>
      api.get<SlotResponse>(
        `/api/availability?provider_id=${appointment.provider.id}&service_id=${appointment.service.id}` +
          `&date_from=${date}&date_to=${date}`,
      ),
    enabled: Boolean(date),
  });

  const mutation = useMutation({
    mutationFn: (startsAt: string) =>
      api.post<Appointment>(`/api/appointments/${appointment.id}/reschedule`, { starts_at: startsAt }),
    onSuccess: () => {
      setSelected(null);
      setError(null);
      toastSuccess(
        "Appointment rescheduled",
        "A new pending request was created for the new time.",
      );
      void queryClient.invalidateQueries();
    },
    onError: (caught) => {
      setError(errorMessage(caught));
      toastError("Could not reschedule", errorMessage(caught));
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Reschedule</CardTitle>
        <CardDescription>
          The current booking becomes Rescheduled and the new time starts as Pending.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="max-w-xs space-y-1">
          <Label htmlFor="reschedule-date">New date</Label>
          <DatePicker
            id="reschedule-date"
            className="w-full"
            value={date}
            from={isoDate(0)}
            to={isoDate(30)}
            onChange={(value) => {
              setDate(value);
              setSelected(null);
            }}
          />
        </div>

        {!date ? (
          <Alert variant="muted" title="Choose a date to see available times" />
        ) : slots.isPending ? (
          <Loading label="Loading available times…" />
        ) : null}
        {slots.isError ? (
          <ErrorState message={errorMessage(slots.error)} retry={() => void slots.refetch()} />
        ) : null}
        {slots.data && slots.data.slots.length === 0 ? (
          <Alert variant="muted" title="No times are available on this date">
            Pick another date to see further options.
          </Alert>
        ) : null}
        {slots.data && slots.data.slots.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {slots.data.slots.map((slot) => (
              <Button
                key={slot}
                size="sm"
                variant={selected === slot ? "default" : "outline"}
                onClick={() => setSelected(slot)}
              >
                {formatTime(slot, timeZone)}
              </Button>
            ))}
          </div>
        ) : null}

        {error ? (
          <Alert variant="error" title="Could not reschedule">
            {error}
          </Alert>
        ) : null}
        <Button
          disabled={!selected || mutation.isPending}
          onClick={() => selected && mutation.mutate(selected)}
        >
          {mutation.isPending ? "Rescheduling…" : "Reschedule to selected time"}
        </Button>
      </CardContent>
    </Card>
  );
}
