"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import * as React from "react";
import { useForm } from "react-hook-form";

import { useAuth } from "@/components/providers";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { api, errorMessage } from "@/lib/api";
import { applyApiFieldErrors } from "@/lib/form-errors";
import type { User } from "@/lib/types";
import { type LoginValues, loginSchema } from "@/lib/validation";

function homeFor(user: User): string {
  if (user.role === "ADMIN") return "/admin";
  if (user.role === "PROVIDER") return "/provider";
  return "/dashboard";
}

function LoginForm() {
  const params = useSearchParams();
  const { refresh } = useAuth();
  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  const signIn = useMutation({
    mutationFn: (values: LoginValues) => api.post<User>("/api/auth/login", values),
    onSuccess: async (user) => {
      await refresh();
      const requested = params.get("next");
      const target = requested && requested.startsWith("/") ? requested : homeFor(user);
      // Full navigation so the session cookie is visible to middleware and the
      // auth context is freshly loaded before a protected page renders.
      window.location.assign(target);
    },
    onError: (caught) => {
      applyApiFieldErrors(form.setError, caught);
    },
  });

  return (
    <div className="mx-auto max-w-md py-8">
      <Card>
        <CardHeader>
          <CardTitle>Sign in</CardTitle>
          <CardDescription>Use the account created for you or your customer account.</CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form
              onSubmit={form.handleSubmit((values) => signIn.mutate(values))}
              className="space-y-4"
              noValidate
            >
              {signIn.isError ? (
                <Alert variant="error" title="Could not sign in">
                  {errorMessage(signIn.error)}
                </Alert>
              ) : null}
              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Email</FormLabel>
                    <FormControl>
                      <Input type="email" autoComplete="email" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Password</FormLabel>
                    <FormControl>
                      <Input type="password" autoComplete="current-password" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <Button type="submit" className="w-full" disabled={signIn.isPending}>
                {signIn.isPending ? "Signing in…" : "Sign in"}
              </Button>
              <p className="text-center text-sm text-muted-foreground">
                New customer?{" "}
                <Link
                  href="/register"
                  className="font-medium text-primary underline-offset-4 hover:underline"
                >
                  Create an account
                </Link>
              </p>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
}

export default function LoginPage() {
  return (
    <React.Suspense fallback={<p className="py-8 text-sm text-muted-foreground">Loading…</p>}>
      <LoginForm />
    </React.Suspense>
  );
}
