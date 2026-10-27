"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import * as React from "react";
import { useForm } from "react-hook-form";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Textarea } from "@/components/ui/input";
import { api, errorMessage } from "@/lib/api";
import type { Appointment, Role } from "@/lib/types";
import { type ReasonValues, reasonSchema } from "@/lib/validation";

type Action = "confirm" | "reject" | "cancel" | "complete";

const LABELS: Record<Action, string> = {
  confirm: "Confirm",
  reject: "Reject",
  cancel: "Cancel appointment",
  complete: "Mark completed",
};

const PATHS: Record<Action, string> = {
  confirm: "confirm",
  reject: "reject",
  cancel: "cancel",
  complete: "complete",
};

export function AppointmentActions({
  appointment,
  role,
}: {
  appointment: Appointment;
  role: Role;
}) {
  const queryClient = useQueryClient();
  const [reasonFor, setReasonFor] = React.useState<Action | null>(null);
  const form = useForm<ReasonValues>({
    resolver: zodResolver(reasonSchema),
    defaultValues: { reason: "" },
  });

  const now = Date.now();
  const starts = new Date(appointment.starts_at).getTime();
  const ends = new Date(appointment.ends_at).getTime();
  const active = appointment.status === "PENDING" || appointment.status === "CONFIRMED";
  const beforeCustomerCutoff = starts - now > 2 * 60 * 60 * 1000;

  const available: Action[] = [];
  if (role === "PROVIDER") {
    if (appointment.status === "PENDING") available.push("confirm", "reject");
    if (appointment.status === "CONFIRMED" && now < ends) available.push("cancel");
    if (appointment.status === "CONFIRMED" && now >= ends) available.push("complete");
  }
  if (role === "CUSTOMER" && active && beforeCustomerCutoff) available.push("cancel");
  if (role === "ADMIN" && active) available.push("cancel");

  const mutation = useMutation({
    mutationFn: ({ action, reason }: { action: Action; reason: string }) =>
      api.post<Appointment>(`/api/appointments/${appointment.id}/${PATHS[action]}`, {
        reason: reason.trim() || null,
      }),
    onSuccess: () => {
      setReasonFor(null);
      form.reset({ reason: "" });
      void queryClient.invalidateQueries();
    },
  });

  function openReason(action: Action) {
    form.reset({ reason: "" });
    setReasonFor(action);
  }

  if (available.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No actions are available for this appointment in its current state.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {mutation.isError && !reasonFor ? (
        <Alert variant="error" title="Action failed">
          {errorMessage(mutation.error)}
        </Alert>
      ) : null}
      <div className="flex flex-wrap gap-2">
        {available.map((action) => (
          <Button
            key={action}
            variant={
              action === "confirm" ? "default" : action === "complete" ? "secondary" : "outline"
            }
            size="sm"
            onClick={() => {
              if (action === "reject" || action === "cancel") {
                openReason(action);
              } else {
                mutation.mutate({ action, reason: "" });
              }
            }}
            disabled={mutation.isPending}
          >
            {LABELS[action]}
          </Button>
        ))}
      </div>

      <Dialog
        open={Boolean(reasonFor)}
        onOpenChange={(open) => {
          if (!open) setReasonFor(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{reasonFor ? LABELS[reasonFor] : "Confirm"}</DialogTitle>
            <DialogDescription>
              The other party can see this note. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          {mutation.isError ? (
            <Alert variant="error" title="Action failed">
              {errorMessage(mutation.error)}
            </Alert>
          ) : null}
          <Form {...form}>
            <form
              id="reason-form"
              className="space-y-3"
              onSubmit={form.handleSubmit((values) => {
                if (!reasonFor) return;
                mutation.mutate({ action: reasonFor, reason: values.reason });
              })}
              noValidate
            >
              <FormField
                control={form.control}
                name="reason"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Reason (optional)</FormLabel>
                    <FormControl>
                      <Textarea
                        {...field}
                        maxLength={500}
                        placeholder="Add a note for the other party"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setReasonFor(null)}>
                  Keep appointment
                </Button>
                <Button type="submit" variant="destructive" disabled={mutation.isPending}>
                  {mutation.isPending
                    ? "Working…"
                    : `Confirm ${reasonFor ? LABELS[reasonFor].toLowerCase() : ""}`}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
