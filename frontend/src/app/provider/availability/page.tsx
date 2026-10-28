"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as React from "react";
import { useForm } from "react-hook-form";

import { ErrorState, Loading } from "@/components/page-state";
import { useAuth } from "@/components/providers";
import { RequireRole } from "@/components/require-role";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { DatePicker } from "@/components/ui/date-picker";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input, Textarea } from "@/components/ui/input";
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
import { applyApiFieldErrors } from "@/lib/form-errors";
import { WEEKDAYS, formatInstant } from "@/lib/format";
import type { Appointment, AvailabilityState, Provider } from "@/lib/types";
import {
  availabilityBreaksSchema,
  availabilityOverridesSchema,
  availabilityWindowsSchema,
  type PracticeValues,
  practiceSchema,
} from "@/lib/validation";

interface WindowRow {
  weekday: number;
  start_time: string;
  end_time: string;
}

interface BreakRow {
  kind: "weekday" | "date";
  weekday: number;
  date: string;
  start_time: string;
  end_time: string;
}

interface OverrideRow {
  date: string;
  is_closed: boolean;
  note: string;
  windows: { start_time: string; end_time: string }[];
}

const short = (value: string) => value.slice(0, 5);

function AvailabilityManager() {
  const { user } = useAuth();
  const providerId = user?.provider_id;
  const queryClient = useQueryClient();
  const [error, setError] = React.useState<string | null>(null);
  const [windows, setWindows] = React.useState<WindowRow[]>([]);
  const [breaks, setBreaks] = React.useState<BreakRow[]>([]);
  const [overrides, setOverrides] = React.useState<OverrideRow[]>([]);
  const practiceForm = useForm<PracticeValues>({
    resolver: zodResolver(practiceSchema),
    defaultValues: { display_name: "", category: "", bio: "", timezone: "" },
  });
  const savedTimezone = React.useRef("");

  const state = useQuery({
    queryKey: ["availability-config", providerId],
    queryFn: () => api.get<AvailabilityState>(`/api/providers/${providerId}/availability`),
    enabled: Boolean(providerId),
  });

  const detail = useQuery({
    queryKey: ["provider", providerId],
    queryFn: () => api.get<Provider>(`/api/providers/${providerId}`),
    enabled: Boolean(providerId),
  });

  const conflicts = useQuery({
    queryKey: ["availability-conflicts", providerId],
    queryFn: () => api.get<Appointment[]>(`/api/providers/${providerId}/availability/conflicts`),
    enabled: Boolean(providerId),
  });

  React.useEffect(() => {
    if (!state.data) return;
    setWindows(
      state.data.windows.map((item) => ({
        weekday: item.weekday,
        start_time: short(item.start_time),
        end_time: short(item.end_time),
      })),
    );
    setBreaks(
      state.data.breaks.map((item) => ({
        kind: item.weekday === null ? "date" : "weekday",
        weekday: item.weekday ?? 0,
        date: item.date ?? "",
        start_time: short(item.start_time),
        end_time: short(item.end_time),
      })),
    );
    setOverrides(
      state.data.overrides.map((item) => ({
        date: item.date,
        is_closed: item.is_closed,
        note: item.note ?? "",
        windows: item.windows.map((window) => ({
          start_time: short(window.start_time),
          end_time: short(window.end_time),
        })),
      })),
    );
  }, [state.data]);

  React.useEffect(() => {
    if (!detail.data) return;
    practiceForm.reset({
      display_name: detail.data.display_name,
      category: detail.data.category,
      bio: detail.data.bio ?? "",
      timezone: detail.data.timezone,
    });
    savedTimezone.current = detail.data.timezone;
  }, [detail.data, practiceForm]);

  const save = useMutation({
    mutationFn: ({ path, body }: { path: string; body: unknown }) =>
      api.put<AvailabilityState>(`/api/providers/${providerId}/availability/${path}`, body),
    onSuccess: () => {
      setError(null);
      toastSuccess("Availability saved", "Your windows, breaks and overrides are up to date.");
      void queryClient.invalidateQueries();
    },
    onError: (caught) => {
      setError(errorMessage(caught));
      toastError("Could not save availability", errorMessage(caught));
    },
  });

  const savePractice = useMutation({
    mutationFn: (values: PracticeValues) =>
      api.patch<Provider>(`/api/providers/${providerId}`, {
        display_name: values.display_name,
        category: values.category,
        bio: values.bio?.trim() || null,
        timezone: values.timezone,
      }),
    onSuccess: (provider) => {
      savedTimezone.current = provider.timezone;
      practiceForm.reset({
        display_name: provider.display_name,
        category: provider.category,
        bio: provider.bio ?? "",
        timezone: provider.timezone,
      });
      void queryClient.invalidateQueries();
      toastSuccess(
        "Practice details saved",
        provider.timezone === timezone ? undefined : `Future slots will use ${provider.timezone}.`,
      );
    },
    onError: (caught) => {
      applyApiFieldErrors(practiceForm.setError, caught);
      toastError("Could not save practice details", errorMessage(caught));
    },
  });

  const deleteOverride = useMutation({
    mutationFn: (date: string) =>
      api.delete<AvailabilityState>(`/api/providers/${providerId}/availability/overrides/${date}`),
    onSuccess: (_state, date) => {
      setError(null);
      toastSuccess("Override removed", date);
      void queryClient.invalidateQueries();
    },
    onError: (caught) => {
      setError(errorMessage(caught));
      toastError("Could not remove the override", errorMessage(caught));
    },
  });

  if (!providerId) return <ErrorState message="Your account has no provider profile." />;
  if (state.isPending || detail.isPending) {
    return (
      <div className="space-y-6" role="status" aria-label="Loading availability…">
        <Skeleton className="h-8 w-52" />
        {[0, 1, 2, 3].map((block) => (
          <div key={block} className="space-y-3">
            <Skeleton className="h-6 w-44" />
            <Skeleton className="h-40 w-full rounded-xl" />
          </div>
        ))}
      </div>
    );
  }
  if (state.isError) {
    return <ErrorState message={errorMessage(state.error)} retry={() => void state.refetch()} />;
  }

  const timezone = practiceForm.watch("timezone");
  const timezoneChanged = savedTimezone.current !== "" && timezone !== savedTimezone.current;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Availability</h1>
        <p className="text-muted-foreground">
          Working windows, breaks and date overrides are interpreted in your practice timezone.
        </p>
      </div>

      {error ? <Alert variant="error" title="Could not save changes">{error}</Alert> : null}

      <Card>
        <CardHeader>
          <CardTitle>Working windows</CardTitle>
          <CardDescription>
            Add one or more windows per weekday. Windows on the same day must not overlap.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {windows.length === 0 ? (
            <p className="text-sm text-muted-foreground">No working windows yet.</p>
          ) : null}
          {windows.map((window, index) => (
            <div key={index} className="flex flex-wrap items-end gap-2">
              <Select
                value={String(window.weekday)}
                onValueChange={(value) => {
                  const next = [...windows];
                  next[index] = { ...window, weekday: Number(value) };
                  setWindows(next);
                }}
              >
                <SelectTrigger aria-label="Weekday" className="w-36">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {WEEKDAYS.map((day, value) => (
                    <SelectItem key={day} value={String(value)}>
                      {day}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Input
                aria-label="Start time"
                type="time"
                className="h-9 w-32"
                value={window.start_time}
                onChange={(event) => {
                  const next = [...windows];
                  next[index] = { ...window, start_time: event.target.value };
                  setWindows(next);
                }}
              />
              <Input
                aria-label="End time"
                type="time"
                className="h-9 w-32"
                value={window.end_time}
                onChange={(event) => {
                  const next = [...windows];
                  next[index] = { ...window, end_time: event.target.value };
                  setWindows(next);
                }}
              />
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setWindows(windows.filter((_, position) => position !== index))}
              >
                Remove
              </Button>
            </div>
          ))}
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() =>
                setWindows([
                  ...windows,
                  { weekday: 0, start_time: "09:00", end_time: "17:00" },
                ])
              }
            >
              Add window
            </Button>
            <Button
              size="sm"
              disabled={save.isPending}
              onClick={() => {
                const parsed = availabilityWindowsSchema.safeParse({ windows });
                if (!parsed.success) {
                  setError(parsed.error.issues[0]?.message ?? "Check your working windows.");
                  return;
                }
                save.mutate({ path: "windows", body: parsed.data });
              }}
            >
              Save windows
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Breaks</CardTitle>
          <CardDescription>Recurring weekday breaks and one-off date breaks are excluded from slots.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {breaks.map((item, index) => (
            <div key={index} className="flex flex-wrap items-end gap-2">
              <Select
                value={item.kind}
                onValueChange={(value) => {
                  const next = [...breaks];
                  next[index] = { ...item, kind: value as "weekday" | "date" };
                  setBreaks(next);
                }}
              >
                <SelectTrigger aria-label="Break type" className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="weekday">Weekly</SelectItem>
                  <SelectItem value="date">One date</SelectItem>
                </SelectContent>
              </Select>
              {item.kind === "weekday" ? (
                <Select
                  value={String(item.weekday)}
                  onValueChange={(value) => {
                    const next = [...breaks];
                    next[index] = { ...item, weekday: Number(value) };
                    setBreaks(next);
                  }}
                >
                  <SelectTrigger aria-label="Break weekday" className="w-36">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {WEEKDAYS.map((day, value) => (
                      <SelectItem key={day} value={String(value)}>
                        {day}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : (
                <DatePicker
                  aria-label="Break date"
                  className="h-9 w-40"
                  value={item.date}
                  onChange={(value) => {
                    const next = [...breaks];
                    next[index] = { ...item, date: value };
                    setBreaks(next);
                  }}
                />
              )}
              <Input
                aria-label="Break start"
                type="time"
                className="h-9 w-32"
                value={item.start_time}
                onChange={(event) => {
                  const next = [...breaks];
                  next[index] = { ...item, start_time: event.target.value };
                  setBreaks(next);
                }}
              />
              <Input
                aria-label="Break end"
                type="time"
                className="h-9 w-32"
                value={item.end_time}
                onChange={(event) => {
                  const next = [...breaks];
                  next[index] = { ...item, end_time: event.target.value };
                  setBreaks(next);
                }}
              />
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setBreaks(breaks.filter((_, position) => position !== index))}
              >
                Remove
              </Button>
            </div>
          ))}
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() =>
                setBreaks([
                  ...breaks,
                  { kind: "weekday", weekday: 0, date: "", start_time: "12:00", end_time: "13:00" },
                ])
              }
            >
              Add break
            </Button>
            <Button
              size="sm"
              disabled={save.isPending}
              onClick={() => {
                const parsed = availabilityBreaksSchema.safeParse({ breaks });
                if (!parsed.success) {
                  setError(parsed.error.issues[0]?.message ?? "Check your breaks.");
                  return;
                }
                save.mutate({
                  path: "breaks",
                  body: {
                    breaks: breaks.map((item) => ({
                      weekday: item.kind === "weekday" ? item.weekday : null,
                      date: item.kind === "date" ? item.date : null,
                      start_time: item.start_time,
                      end_time: item.end_time,
                    })),
                  },
                });
              }}
            >
              Save breaks
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Date overrides</CardTitle>
          <CardDescription>
            A closed date removes all slots. An open date replaces the weekly windows with its own.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {overrides.map((override, index) => (
            <div key={index} className="space-y-2 rounded-md border p-3">
              <div className="flex flex-wrap items-end gap-2">
                <div className="space-y-1">
                  <Label htmlFor={`override-date-${index}`}>Date</Label>
                  <DatePicker
                    id={`override-date-${index}`}
                    className="h-9 w-40"
                    value={override.date}
                    onChange={(value) => {
                      const next = [...overrides];
                      next[index] = { ...override, date: value };
                      setOverrides(next);
                    }}
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor={`override-closed-${index}`}>Closed</Label>
                  <Select
                    value={override.is_closed ? "closed" : "open"}
                    onValueChange={(value) => {
                      const next = [...overrides];
                      next[index] = { ...override, is_closed: value === "closed" };
                      setOverrides(next);
                    }}
                  >
                    <SelectTrigger
                      id={`override-closed-${index}`}
                      aria-label="Closed"
                      className="w-40"
                    >
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="open">Open with hours</SelectItem>
                      <SelectItem value="closed">Closed all day</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setOverrides(overrides.filter((_, position) => position !== index))}
                >
                  Remove
                </Button>
              </div>
              {!override.is_closed ? (
                <div className="space-y-2">
                  {override.windows.map((window, windowIndex) => (
                    <div key={windowIndex} className="flex flex-wrap items-end gap-2">
                      <Input
                        aria-label="Override start"
                        type="time"
                        className="h-9 w-32"
                        value={window.start_time}
                        onChange={(event) => {
                          const next = [...overrides];
                          const windowsCopy = [...override.windows];
                          windowsCopy[windowIndex] = {
                            ...window,
                            start_time: event.target.value,
                          };
                          next[index] = { ...override, windows: windowsCopy };
                          setOverrides(next);
                        }}
                      />
                      <Input
                        aria-label="Override end"
                        type="time"
                        className="h-9 w-32"
                        value={window.end_time}
                        onChange={(event) => {
                          const next = [...overrides];
                          const windowsCopy = [...override.windows];
                          windowsCopy[windowIndex] = { ...window, end_time: event.target.value };
                          next[index] = { ...override, windows: windowsCopy };
                          setOverrides(next);
                        }}
                      />
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          const next = [...overrides];
                          next[index] = {
                            ...override,
                            windows: override.windows.filter((_, position) => position !== windowIndex),
                          };
                          setOverrides(next);
                        }}
                      >
                        Remove
                      </Button>
                    </div>
                  ))}
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      const next = [...overrides];
                      next[index] = {
                        ...override,
                        windows: [...override.windows, { start_time: "10:00", end_time: "14:00" }],
                      };
                      setOverrides(next);
                    }}
                  >
                    Add hours
                  </Button>
                </div>
              ) : null}
            </div>
          ))}
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() =>
                setOverrides([
                  ...overrides,
                  { date: "", is_closed: true, note: "", windows: [] },
                ])
              }
            >
              Add override
            </Button>
            <Button
              size="sm"
              disabled={save.isPending}
              onClick={() => {
                const parsed = availabilityOverridesSchema.safeParse({ overrides });
                if (!parsed.success) {
                  setError(parsed.error.issues[0]?.message ?? "Check your date overrides.");
                  return;
                }
                save.mutate({ path: "overrides", body: parsed.data });
              }}
            >
              Save overrides
            </Button>
          </div>
          {state.data && state.data.overrides.length > 0 ? (
            <div className="space-y-1">
              <p className="text-sm font-medium">Remove a saved override</p>
              <div className="flex flex-wrap gap-2">
                {state.data.overrides.map((item) => (
                  <Button
                    key={item.date}
                    size="sm"
                    variant="ghost"
                    onClick={() => deleteOverride.mutate(item.date)}
                  >
                    Delete {item.date}
                  </Button>
                ))}
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Practice details</CardTitle>
          <CardDescription>Name, category, biography and timezone.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Form {...practiceForm}>
            <form
              className="space-y-3"
              onSubmit={practiceForm.handleSubmit((values) => savePractice.mutate(values))}
              noValidate
            >
              {savePractice.isError ? (
                <Alert variant="error" title="Could not save practice details">
                  {errorMessage(savePractice.error)}
                </Alert>
              ) : null}
              <div className="grid gap-3 sm:grid-cols-2">
                <FormField
                  control={practiceForm.control}
                  name="display_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Display name</FormLabel>
                      <FormControl>
                        <Input {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={practiceForm.control}
                  name="category"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Category</FormLabel>
                      <FormControl>
                        <Input {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              <FormField
                control={practiceForm.control}
                name="bio"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Biography</FormLabel>
                    <FormControl>
                      <Textarea {...field} value={field.value ?? ""} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={practiceForm.control}
                name="timezone"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>IANA timezone</FormLabel>
                    <FormControl>
                      <Input {...field} list="timezone-options" />
                    </FormControl>
                    <datalist id="timezone-options">
                      <option value="UTC" />
                      <option value="Europe/London" />
                      <option value="Europe/Berlin" />
                      <option value="America/New_York" />
                      <option value="America/Los_Angeles" />
                      <option value="Asia/Tokyo" />
                      <option value="Australia/Sydney" />
                    </datalist>
                    <FormMessage />
                  </FormItem>
                )}
              />
              {timezoneChanged ? (
                <Alert variant="info" title="Changing your timezone">
                  Future availability will be reinterpreted in {timezone}. Existing appointments keep
                  their original instants and will not move.
                </Alert>
              ) : null}
              <Button type="submit" disabled={savePractice.isPending}>
                {savePractice.isPending ? "Saving…" : "Save practice details"}
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Appointments outside availability</CardTitle>
          <CardDescription>
            These are unchanged and identified for manual handling after a schedule edit.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {conflicts.isPending ? <Loading label="Checking conflicts…" /> : null}
          {conflicts.data && conflicts.data.length === 0 ? (
            <p className="text-sm text-muted-foreground">Every active appointment fits your schedule.</p>
          ) : null}
          {conflicts.data?.map((appointment) => (
            <p key={appointment.id} className="text-sm">
              {formatInstant(appointment.starts_at, appointment.provider.timezone)} ·{" "}
              {appointment.customer.full_name} · {appointment.status}
            </p>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

export default function ProviderAvailabilityPage() {
  return (
    <RequireRole roles={["PROVIDER"]}>
      <AvailabilityManager />
    </RequireRole>
  );
}
