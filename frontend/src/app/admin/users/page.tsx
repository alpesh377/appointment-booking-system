"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as React from "react";
import { useForm } from "react-hook-form";

import { ErrorState, Loading, NoItems } from "@/components/page-state";
import { RequireRole } from "@/components/require-role";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input, Textarea } from "@/components/ui/input";
import { api, errorMessage } from "@/lib/api";
import { applyApiFieldErrors } from "@/lib/form-errors";
import type { Provider, User } from "@/lib/types";
import {
  type ProviderAccountValues,
  providerAccountSchema,
  type ProviderProfileValues,
  providerProfileSchema,
} from "@/lib/validation";

const EMPTY_PROVIDER: ProviderAccountValues = {
  email: "",
  password: "",
  full_name: "",
  display_name: "",
  category: "",
  bio: "",
  phone: "",
  timezone: "UTC",
};

const EMPTY_PROFILE: ProviderProfileValues = {
  display_name: "",
  category: "",
  bio: "",
  timezone: "",
};

type PendingToggle = {
  kind: "customer" | "provider";
  id: string;
  active: boolean;
  name: string;
};

function UsersManager() {
  const queryClient = useQueryClient();
  const [search, setSearch] = React.useState("");
  const [editing, setEditing] = React.useState<Provider | null>(null);
  const [pendingToggle, setPendingToggle] = React.useState<PendingToggle | null>(null);

  const createForm = useForm<ProviderAccountValues>({
    resolver: zodResolver(providerAccountSchema),
    defaultValues: EMPTY_PROVIDER,
  });
  const editForm = useForm<ProviderProfileValues>({
    resolver: zodResolver(providerProfileSchema),
    defaultValues: EMPTY_PROFILE,
  });

  const customers = useQuery({
    queryKey: ["admin", "customers", search],
    queryFn: () =>
      api.get<User[]>(`/api/admin/customers${search ? `?q=${encodeURIComponent(search)}` : ""}`),
  });

  const providers = useQuery({
    queryKey: ["admin", "providers"],
    queryFn: () => api.get<Provider[]>("/api/admin/providers"),
  });

  const act = useMutation({
    mutationFn: ({ path }: { path: string }) => api.post(path, {}),
    onSuccess: () => {
      void queryClient.invalidateQueries();
    },
  });

  const updateProvider = useMutation({
    mutationFn: (values: ProviderProfileValues) =>
      api.patch<Provider>(`/api/providers/${editing?.id}`, {
        display_name: values.display_name,
        category: values.category,
        bio: values.bio?.trim() || null,
        timezone: values.timezone,
      }),
    onSuccess: () => {
      setEditing(null);
      void queryClient.invalidateQueries();
    },
    onError: (caught) => {
      applyApiFieldErrors(editForm.setError, caught);
    },
  });

  const createProvider = useMutation({
    mutationFn: (values: ProviderAccountValues) =>
      api.post<Provider>("/api/providers", {
        email: values.email,
        password: values.password,
        full_name: values.full_name,
        display_name: values.display_name,
        category: values.category,
        bio: values.bio?.trim() || null,
        phone: values.phone?.trim() || null,
        timezone: values.timezone,
      }),
    onSuccess: () => {
      createForm.reset(EMPTY_PROVIDER);
      void queryClient.invalidateQueries();
    },
    onError: (caught) => {
      applyApiFieldErrors(createForm.setError, caught);
    },
  });

  function openEditor(provider: Provider) {
    setEditing(provider);
    editForm.reset({
      display_name: provider.display_name,
      category: provider.category,
      bio: provider.bio ?? "",
      timezone: provider.timezone,
    });
  }

  const toggle = pendingToggle;
  const toggleMessage = toggle
    ? toggle.kind === "customer"
      ? toggle.active
        ? "Deactivating blocks sign-in. Existing and future appointments stay unchanged — review them in Appointments."
        : "Reactivate this customer so they can sign in again?"
      : toggle.active
        ? "Deactivating removes the provider from discovery. Future appointments stay unchanged — review them in Appointments."
        : "Reactivate this provider and make them bookable again?"
    : "";

  function confirmToggle() {
    if (!toggle) return;
    const path =
      toggle.kind === "customer"
        ? `/api/admin/users/${toggle.id}/${toggle.active ? "deactivate" : "reactivate"}`
        : `/api/providers/${toggle.id}/${toggle.active ? "deactivate" : "reactivate"}`;
    act.mutate({ path });
    setPendingToggle(null);
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Users</h1>
        <p className="text-muted-foreground">
          Customer accounts and provider accounts. Deactivation never deletes history.
        </p>
      </div>

      {act.isError ? (
        <Alert variant="error" title="Action failed">
          {errorMessage(act.error)}
        </Alert>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Customers</CardTitle>
          <CardDescription>Search by name or email.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search customers"
            aria-label="Search customers"
            className="sm:max-w-sm"
          />
          {customers.isPending ? <Loading label="Loading customers…" /> : null}
          {customers.isError ? (
            <ErrorState message={errorMessage(customers.error)} retry={() => void customers.refetch()} />
          ) : null}
          {customers.data && customers.data.length === 0 ? (
            <NoItems title="No customers found" />
          ) : null}
          {customers.data && customers.data.length > 0 ? (
            <ul className="divide-y">
              {customers.data.map((user) => (
                <li key={user.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                  <div>
                    <p className="font-medium">{user.full_name}</p>
                    <p className="text-sm text-muted-foreground">{user.email}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className={user.is_active ? "border-emerald-200" : "border-border"}>
                      {user.is_active ? "Active" : "Deactivated"}
                    </Badge>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() =>
                        setPendingToggle({
                          kind: "customer",
                          id: user.id,
                          active: user.is_active,
                          name: user.full_name,
                        })
                      }
                    >
                      {user.is_active ? "Deactivate" : "Reactivate"}
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Providers</CardTitle>
          <CardDescription>Includes deactivated providers.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {providers.isPending ? <Loading label="Loading providers…" /> : null}
          {providers.isError ? (
            <ErrorState message={errorMessage(providers.error)} retry={() => void providers.refetch()} />
          ) : null}
          {providers.data && providers.data.length === 0 ? <NoItems title="No providers yet" /> : null}
          {providers.data && providers.data.length > 0 ? (
            <ul className="divide-y">
              {providers.data.map((provider) => (
                <li key={provider.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                  <div>
                    <p className="font-medium">{provider.display_name}</p>
                    <p className="text-sm text-muted-foreground">
                      {provider.category} · {provider.email} · {provider.timezone}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className={provider.is_active ? "border-emerald-200" : "border-border"}>
                      {provider.is_active ? "Active" : "Deactivated"}
                    </Badge>
                    <Button size="sm" variant="ghost" onClick={() => openEditor(provider)}>
                      Edit
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() =>
                        setPendingToggle({
                          kind: "provider",
                          id: provider.id,
                          active: provider.is_active,
                          name: provider.display_name,
                        })
                      }
                    >
                      {provider.is_active ? "Deactivate" : "Reactivate"}
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Create a provider account</CardTitle>
          <CardDescription>
            Providers cannot self-register. The account and profile are created together.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {createProvider.isError ? (
            <Alert variant="error" title="Could not create the provider" className="mb-3">
              {errorMessage(createProvider.error)}
            </Alert>
          ) : null}
          <Form {...createForm}>
            <form
              className="grid gap-3 sm:grid-cols-2"
              onSubmit={createForm.handleSubmit((values) => createProvider.mutate(values))}
              noValidate
            >
              <FormField
                control={createForm.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Email</FormLabel>
                    <FormControl>
                      <Input type="email" autoComplete="off" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={createForm.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Initial password</FormLabel>
                    <FormControl>
                      <Input type="password" autoComplete="new-password" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={createForm.control}
                name="full_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Full name</FormLabel>
                    <FormControl>
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={createForm.control}
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
                control={createForm.control}
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
              <FormField
                control={createForm.control}
                name="timezone"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>IANA timezone</FormLabel>
                    <FormControl>
                      <Input {...field} list="admin-timezone-options" />
                    </FormControl>
                    <datalist id="admin-timezone-options">
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
              <FormField
                control={createForm.control}
                name="bio"
                render={({ field }) => (
                  <FormItem className="sm:col-span-2">
                    <FormLabel>Biography (optional)</FormLabel>
                    <FormControl>
                      <Textarea {...field} value={field.value ?? ""} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <div className="sm:col-span-2">
                <Button type="submit" disabled={createProvider.isPending}>
                  {createProvider.isPending ? "Creating…" : "Create provider"}
                </Button>
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>

      <Dialog open={Boolean(editing)} onOpenChange={(open) => (open ? undefined : setEditing(null))}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit provider</DialogTitle>
            <DialogDescription>
              Changes apply to the public profile. {editing?.email ? `Account: ${editing.email}` : null}
            </DialogDescription>
          </DialogHeader>
          {updateProvider.isError ? (
            <Alert variant="error" title="Could not save">
              {errorMessage(updateProvider.error)}
            </Alert>
          ) : null}
          <Form {...editForm}>
            <form
              className="grid gap-3 sm:grid-cols-2"
              onSubmit={editForm.handleSubmit((values) => updateProvider.mutate(values))}
              noValidate
            >
              <FormField
                control={editForm.control}
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
                control={editForm.control}
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
              <FormField
                control={editForm.control}
                name="timezone"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>IANA timezone</FormLabel>
                    <FormControl>
                      <Input {...field} list="edit-timezone-options" />
                    </FormControl>
                    <datalist id="edit-timezone-options">
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
              <FormField
                control={editForm.control}
                name="bio"
                render={({ field }) => (
                  <FormItem className="sm:col-span-2">
                    <FormLabel>Biography</FormLabel>
                    <FormControl>
                      <Textarea {...field} value={field.value ?? ""} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <DialogFooter className="sm:col-span-2">
                <Button type="button" variant="outline" onClick={() => setEditing(null)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={updateProvider.isPending}>
                  {updateProvider.isPending ? "Saving…" : "Save provider"}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      <AlertDialog
        open={Boolean(pendingToggle)}
        onOpenChange={(open) => (open ? undefined : setPendingToggle(null))}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {toggle?.active ? "Deactivate" : "Reactivate"} {toggle?.name}?
            </AlertDialogTitle>
            <AlertDialogDescription>{toggleMessage}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep as is</AlertDialogCancel>
            <AlertDialogAction onClick={confirmToggle}>
              {toggle?.active ? "Deactivate" : "Reactivate"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

export default function AdminUsersPage() {
  return (
    <RequireRole roles={["ADMIN"]}>
      <UsersManager />
    </RequireRole>
  );
}
