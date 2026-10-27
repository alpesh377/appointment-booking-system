"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";

import { ErrorState, NoItems } from "@/components/page-state";
import { useAuth } from "@/components/providers";
import { RequireRole } from "@/components/require-role";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { toastError, toastSuccess } from "@/components/ui/toast";
import { api, errorMessage } from "@/lib/api";
import { applyApiFieldErrors } from "@/lib/form-errors";
import type { Service } from "@/lib/types";
import { type ServiceValues, serviceSchema } from "@/lib/validation";

const SERVICE_DEFAULTS: ServiceValues = { name: "", category: "", duration_minutes: 30 };

function ServicesManager() {
  const { user } = useAuth();
  const providerId = user?.provider_id;
  const queryClient = useQueryClient();
  const form = useForm<ServiceValues>({
    resolver: zodResolver(serviceSchema),
    defaultValues: SERVICE_DEFAULTS,
  });

  const services = useQuery({
    queryKey: ["provider-services"],
    queryFn: () => api.get<Service[]>("/api/provider/services"),
    enabled: Boolean(providerId),
  });

  const create = useMutation({
    mutationFn: (values: ServiceValues) =>
      api.post<Service>(`/api/providers/${providerId}/services`, {
        name: values.name,
        category: values.category,
        duration_minutes: values.duration_minutes,
      }),
    onSuccess: (service) => {
      form.reset(SERVICE_DEFAULTS);
      toastSuccess("Service added", `${service.name} is now bookable by customers.`);
      void queryClient.invalidateQueries();
    },
    onError: (caught) => {
      applyApiFieldErrors(form.setError, caught);
      toastError("Could not save the service", errorMessage(caught));
    },
  });

  const deactivate = useMutation({
    mutationFn: (id: string) => api.post<Service>(`/api/services/${id}/deactivate`),
    onSuccess: () => {
      toastSuccess("Service deactivated");
      void queryClient.invalidateQueries();
    },
    onError: (caught) => toastError("Could not deactivate", errorMessage(caught)),
  });

  if (!providerId) return <ErrorState message="Your account has no provider profile." />;
  if (services.isPending) {
    return (
      <div className="space-y-6" role="status" aria-label="Loading services…">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-24 w-full rounded-xl" />
        {[0, 1, 2].map((row) => (
          <Skeleton key={row} className="h-16 w-full rounded-xl" />
        ))}
      </div>
    );
  }
  if (services.isError) {
    return <ErrorState message={errorMessage(services.error)} retry={() => void services.refetch()} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Services</h1>
        <p className="text-muted-foreground">
          Every service carries its own duration. Durations run from 15 to 480 minutes in steps of 5.
        </p>
      </div>

      {create.isError ? (
        <Alert variant="error" title="Could not save">
          {errorMessage(create.error)}
        </Alert>
      ) : null}
      {deactivate.isError ? (
        <Alert variant="error" title="Could not deactivate">
          {errorMessage(deactivate.error)}
        </Alert>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Add a service</CardTitle>
          <CardDescription>
            Customers book a specific service, and the slot grid follows its duration.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form
              className="grid gap-3 sm:grid-cols-4"
              onSubmit={form.handleSubmit((values) => create.mutate(values))}
              noValidate
            >
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Name</FormLabel>
                    <FormControl>
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
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
                control={form.control}
                name="duration_minutes"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Duration (minutes)</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        inputMode="numeric"
                        min={15}
                        max={480}
                        step={5}
                        name={field.name}
                        ref={field.ref}
                        onBlur={field.onBlur}
                        value={Number.isNaN(field.value) ? "" : field.value}
                        onChange={(event) => field.onChange(event.target.valueAsNumber)}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <div className="flex items-start pt-5">
                <Button type="submit" className="w-full" disabled={create.isPending}>
                  {create.isPending ? "Adding…" : "Add service"}
                </Button>
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>

      {services.data && services.data.length === 0 ? (
        <NoItems
          title="No services yet"
          description="Add your first service so customers can book you."
        />
      ) : null}

      {services.data && services.data.length > 0 ? (
        <div className="grid gap-3">
          {services.data.map((service) => (
            <Card key={service.id}>
              <CardContent className="flex flex-wrap items-center justify-between gap-3 pt-6">
                <div>
                  <p className="font-medium">{service.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {service.category} · {service.duration_minutes} minutes
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge className={service.is_active ? "border-emerald-200" : "border-border"}>
                    {service.is_active ? "Active" : "Inactive"}
                  </Badge>
                  {service.is_active ? (
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={deactivate.isPending}
                      onClick={() => deactivate.mutate(service.id)}
                    >
                      Deactivate
                    </Button>
                  ) : null}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export default function ProviderServicesPage() {
  return (
    <RequireRole roles={["PROVIDER"]}>
      <ServicesManager />
    </RequireRole>
  );
}
