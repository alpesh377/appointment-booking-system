"use client";

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ErrorState, Loading } from "@/components/page-state";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
  });

  const mutation = useMutation({
    mutationFn: (startsAt: string) =>
      api.post<Appointment>(`/api/appointments/${appointment.id}/reschedule`, { starts_at: startsAt }),
    onSuccess: () => {
      setSelected(null);
      setError(null);
      void queryClient.invalidateQueries();
    },
    onError: (caught) => setError(errorMessage(caught)),
  });

  return (
    <div className="space-y-3 rounded-lg border p-4">
      <div>
        <h3 className="font-medium">Reschedule</h3>
        <p className="text-sm text-muted-foreground">
          The current booking becomes Rescheduled and the new time starts as Pending.
        </p>
      </div>
      <div className="max-w-xs space-y-1">
        <Label htmlFor="reschedule-date">New date</Label>
        <Input
          id="reschedule-date"
          type="date"
          value={date}
          min={isoDate(0)}
          max={isoDate(30)}
          onChange={(event) => {
            setDate(event.target.value);
            setSelected(null);
          }}
        />
      </div>

      {slots.isPending ? <Loading label="Loading available times…" /> : null}
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

      {error ? <Alert variant="error" title="Could not reschedule">{error}</Alert> : null}
      <Button
        disabled={!selected || mutation.isPending}
        onClick={() => selected && mutation.mutate(selected)}
      >
        {mutation.isPending ? "Rescheduling…" : "Reschedule to selected time"}
      </Button>
    </div>
  );
}
