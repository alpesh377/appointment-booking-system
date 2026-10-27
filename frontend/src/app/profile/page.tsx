"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import * as React from "react";
import { useForm } from "react-hook-form";

import { Loading } from "@/components/page-state";
import { useAuth } from "@/components/providers";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { api, errorMessage } from "@/lib/api";
import { applyApiFieldErrors } from "@/lib/form-errors";
import type { User } from "@/lib/types";
import { type ProfileValues, profileSchema } from "@/lib/validation";

export default function ProfilePage() {
  const { user, loading, refresh } = useAuth();
  const form = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: { full_name: "", phone: "" },
  });

  React.useEffect(() => {
    if (user) {
      form.reset({ full_name: user.full_name ?? "", phone: user.phone ?? "" });
    }
  }, [user, form]);

  const save = useMutation({
    mutationFn: (values: ProfileValues) =>
      api.patch<User>("/api/auth/me", {
        full_name: values.full_name,
        phone: values.phone?.trim() || null,
      }),
    onSuccess: async (updated) => {
      form.reset({ full_name: updated.full_name ?? "", phone: updated.phone ?? "" });
      await refresh();
    },
    onError: (caught) => {
      applyApiFieldErrors(form.setError, caught);
    },
  });

  if (loading) return <Loading label="Loading profile…" />;
  if (!user) return <Loading label="Redirecting to sign in…" />;

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">My profile</h1>
        <p className="text-muted-foreground">Update the details attached to your account.</p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Account</CardTitle>
          <CardDescription>
            {user.email} · {user.role.charAt(0) + user.role.slice(1).toLowerCase()}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form
              className="space-y-4"
              onSubmit={form.handleSubmit((values) => save.mutate(values))}
              noValidate
            >
              {save.isError ? (
                <Alert variant="error" title="Could not save">
                  {errorMessage(save.error)}
                </Alert>
              ) : null}
              {save.isSuccess ? <Alert variant="success" title="Profile updated" /> : null}
              <FormField
                control={form.control}
                name="full_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Full name</FormLabel>
                    <FormControl>
                      <Input autoComplete="name" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="phone"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Phone</FormLabel>
                    <FormControl>
                      <Input type="tel" autoComplete="tel" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <Button type="submit" disabled={save.isPending}>
                {save.isPending ? "Saving…" : "Save changes"}
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
}
