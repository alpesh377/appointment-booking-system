"use client";

import * as React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { FadeIn } from "@/components/motion";
import { ErrorState, Loading, NoItems } from "@/components/page-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, errorMessage } from "@/lib/api";
import type { ProviderSummary } from "@/lib/types";

export default function ProviderListingPage() {
  const [term, setTerm] = React.useState("");
  const [query, setQuery] = React.useState("");

  const providers = useQuery({
    queryKey: ["providers", query],
    queryFn: () =>
      api.get<ProviderSummary[]>(`/api/providers${query ? `?q=${encodeURIComponent(query)}` : ""}`),
  });

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Find a service provider</h1>
        <p className="max-w-2xl text-muted-foreground">
          Browse providers by name or by the category of the services they offer.
        </p>
      </div>

      <form
        className="flex flex-col gap-2 sm:flex-row sm:items-center"
        onSubmit={(event) => {
          event.preventDefault();
          setQuery(term.trim());
        }}
      >
        <Input
          value={term}
          onChange={(event) => setTerm(event.target.value)}
          placeholder="Search by provider name or service category"
          aria-label="Search providers"
          className="sm:max-w-md"
        />
        <div className="flex gap-2">
          <Button type="submit">Search</Button>
          {query ? (
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                setTerm("");
                setQuery("");
              }}
            >
              Clear
            </Button>
          ) : null}
        </div>
      </form>

      {providers.isPending ? <Loading label="Loading providers…" /> : null}
      {providers.isError ? (
        <ErrorState message={errorMessage(providers.error)} retry={() => void providers.refetch()} />
      ) : null}
      {providers.data && providers.data.length === 0 ? (
        <NoItems
          title={query ? `No providers found for “${query}”` : "No providers are available yet"}
          description={
            query
              ? "Try a different name or service category."
              : "An administrator has not published any providers."
          }
        />
      ) : null}
      {providers.data && providers.data.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {providers.data.map((provider, index) => (
            <FadeIn key={provider.id} delay={index * 0.03}>
              <Card className="flex h-full flex-col">
                <CardHeader>
                  <CardTitle>{provider.display_name}</CardTitle>
                  <CardDescription>{provider.category}</CardDescription>
                </CardHeader>
                <CardContent className="flex flex-1 flex-col justify-between gap-4">
                  <div className="space-y-2">
                    <p className="text-sm text-muted-foreground">Times shown in {provider.timezone}</p>
                    <div className="flex flex-wrap gap-1">
                      {provider.durations.length === 0 ? (
                        <span className="text-sm text-muted-foreground">No services listed yet</span>
                      ) : (
                        provider.durations.map((duration) => (
                          <Badge key={duration} className="border-border">
                            {duration} min
                          </Badge>
                        ))
                      )}
                    </div>
                  </div>
                  <Link
                    href={`/providers/${provider.id}`}
                    className="text-sm font-medium text-primary underline-offset-4 hover:underline"
                  >
                    View profile and availability →
                  </Link>
                </CardContent>
              </Card>
            </FadeIn>
          ))}
        </div>
      ) : null}
    </div>
  );
}
