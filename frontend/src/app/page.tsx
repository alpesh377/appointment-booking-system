"use client";

import * as React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { UsersIcon } from "lucide-react";

import {
  Pressable,
  StaggerGroup,
  StaggerItem,
  Swap,
} from "@/components/motion";
import { ErrorState } from "@/components/page-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { api, errorMessage } from "@/lib/api";
import type { ProviderSummary } from "@/lib/types";

const SEARCH_DEBOUNCE_MS = 300;

function ProviderCardSkeleton() {
  return (
    <div aria-hidden className="flex h-full flex-col rounded-xl border bg-card p-6 shadow-xs">
      <div className="space-y-2">
        <Skeleton className="h-5 w-2/3" />
        <Skeleton className="h-4 w-1/3" />
      </div>
      <div className="mt-4 flex-1 space-y-3">
        <Skeleton className="h-4 w-1/2" />
        <div className="flex gap-2">
          <Skeleton className="h-6 w-20 rounded-full" />
          <Skeleton className="h-6 w-16 rounded-full" />
        </div>
      </div>
      <Skeleton className="h-4 w-40" />
    </div>
  );
}

export default function ProviderListingPage() {
  const [term, setTerm] = React.useState("");
  const [query, setQuery] = React.useState("");

  // Live search: query trails the typed term by a debounce so filtering
  // happens while typing; submit only needs to be harmless.
  React.useEffect(() => {
    const trimmed = term.trim();
    const timer = setTimeout(() => setQuery(trimmed), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [term]);

  const providers = useQuery({
    queryKey: ["providers", query],
    queryFn: () =>
      api.get<ProviderSummary[]>(`/api/providers${query ? `?q=${encodeURIComponent(query)}` : ""}`),
  });

  const count = providers.data?.length ?? 0;
  const showEmpty = providers.data && count === 0;

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Find a service provider</h1>
        <p className="max-w-2xl text-muted-foreground">
          Browse providers by name or by the category of the services they offer.
        </p>
      </div>

      <form
        role="search"
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
          {term || query ? (
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

      <p aria-live="polite" className="text-sm text-muted-foreground">
        {providers.isPending || providers.isError
          ? ""
          : query
            ? `${count} ${count === 1 ? "provider matches" : "providers match"} “${query}”`
            : count > 0
              ? `${count} ${count === 1 ? "provider" : "providers"} available`
              : ""}
      </p>

      {providers.isError ? (
        <ErrorState message={errorMessage(providers.error)} retry={() => void providers.refetch()} />
      ) : null}

      {providers.isPending ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" role="status" aria-label="Loading providers">
          <ProviderCardSkeleton />
          <ProviderCardSkeleton />
          <ProviderCardSkeleton />
          <ProviderCardSkeleton />
          <ProviderCardSkeleton />
          <ProviderCardSkeleton />
        </div>
      ) : null}

      {showEmpty ? (
        <Empty className="rounded-xl border">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <UsersIcon />
            </EmptyMedia>
            <EmptyTitle>
              {query ? `No providers found for “${query}”` : "No providers are available yet"}
            </EmptyTitle>
            <EmptyDescription>
              {query
                ? "Try a different name or service category."
                : "An administrator has not published any providers."}
            </EmptyDescription>
          </EmptyHeader>
          <EmptyContent>
            {query ? (
              <Button variant="outline" onClick={() => setTerm("")}>
                Clear the search
              </Button>
            ) : null}
          </EmptyContent>
        </Empty>
      ) : null}

      {providers.data && count > 0 ? (
        <Swap swapKey={query}>
          <StaggerGroup className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {providers.data.map((provider) => (
              <StaggerItem key={provider.id} className="h-full">
                <Pressable lift className="h-full">
                  <Card className="flex h-full flex-col">
                    <CardHeader>
                      <CardTitle>{provider.display_name}</CardTitle>
                      <CardDescription>{provider.category}</CardDescription>
                    </CardHeader>
                    <CardContent className="flex flex-1 flex-col justify-between gap-4">
                      <div className="space-y-2">
                        <p className="text-sm text-muted-foreground">
                          Times shown in {provider.timezone}
                        </p>
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
                </Pressable>
              </StaggerItem>
            ))}
          </StaggerGroup>
        </Swap>
      ) : null}
    </div>
  );
}
