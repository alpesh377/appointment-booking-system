import { Alert, EmptyState } from "@/components/ui/alert";

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-muted-foreground/30 border-t-muted-foreground" />
      {label}
    </div>
  );
}

export function ErrorState({ message, retry }: { message: string; retry?: () => void }) {
  return (
    <div className="py-4">
      <Alert variant="error" title="Something went wrong">
        <p>{message}</p>
        {retry ? (
          <button type="button" onClick={retry} className="mt-2 text-sm font-medium underline">
            Try again
          </button>
        ) : null}
      </Alert>
    </div>
  );
}

export function NoItems({ title, description }: { title: string; description?: string }) {
  return <EmptyState title={title} description={description} />;
}
