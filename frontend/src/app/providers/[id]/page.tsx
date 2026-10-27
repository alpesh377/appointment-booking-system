"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

import { Loading } from "@/components/page-state";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, ApiError, errorMessage } from "@/lib/api";
import type { Provider } from "@/lib/types";

export default function ProviderDetailPage() {
  const params = useParams<{ id: string }>();
  const provider = useQuery({
    queryKey: ["provider", params.id],
    queryFn: () => api.get<Provider>(`/api/providers/${params.id}`),
    retry: false,
  });

  if (provider.isPending) return <Loading label="Loading provider…" />;
  if (provider.isError) {
    const notFound = provider.error instanceof ApiError && provider.error.status === 404;
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold">Provider not available</h1>
        <p className="text-muted-foreground">
          {notFound
            ? "This provider cannot be found or is no longer accepting bookings."
            : errorMessage(provider.error)}
        </p>
        <Link href="/" className="text-sm font-medium text-primary underline-offset-4 hover:underline">
          ← Back to all providers
        </Link>
      </div>
    );
  }

  const data = provider.data;
  return (
    <div className="space-y-6">
      <Link href="/" className="text-sm font-medium text-primary underline-offset-4 hover:underline">
        ← Back to all providers
      </Link>

      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <div className="space-y-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{data.display_name}</h1>
            <p className="text-muted-foreground">{data.category}</p>
          </div>
          {data.bio ? <p className="max-w-2xl leading-relaxed">{data.bio}</p> : null}
          <Card>
            <CardHeader>
              <CardTitle>Profile</CardTitle>
              <CardDescription>Contact details and timezone</CardDescription>
            </CardHeader>
            <CardContent className="space-y-1 text-sm">
              {data.full_name ? <p>Provider: {data.full_name}</p> : null}
              {data.email ? <p>Email: {data.email}</p> : null}
              {data.phone ? <p>Phone: {data.phone}</p> : null}
              <p>Timezone: {data.timezone}</p>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Services</CardTitle>
            <CardDescription>Choose a service to see available times.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {data.services.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                This provider has no active services yet.
              </p>
            ) : (
              data.services.map((service) => (
                <div key={service.id} className="rounded-md border p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="font-medium">{service.name}</p>
                      <p className="text-sm text-muted-foreground">{service.category}</p>
                    </div>
                    <Badge className="border-border">{service.duration_minutes} min</Badge>
                  </div>
                  <Link
                    href={`/providers/${data.id}/book?service=${service.id}`}
                    className="mt-2 inline-block text-sm font-medium text-primary underline-offset-4 hover:underline"
                  >
                    Book this service →
                  </Link>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
