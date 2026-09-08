import { Loader2, AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

export function PageLoader() {
  return (
    <div className="flex min-h-[60vh] w-full items-center justify-center" data-testid="page-loader">
      <Loader2 className="h-8 w-8 animate-spin text-primary" strokeWidth={1.5} />
    </div>
  );
}

export function Spinner({ className = "" }) {
  return <Loader2 className={`h-5 w-5 animate-spin ${className}`} strokeWidth={1.5} />;
}

export function CardSkeleton({ className = "" }) {
  return (
    <div className={`rounded-xl border border-border bg-card p-6 ${className}`}>
      <Skeleton className="mb-4 h-4 w-24" />
      <Skeleton className="mb-2 h-10 w-32" />
      <Skeleton className="h-4 w-full" />
    </div>
  );
}

export function ErrorState({ title = "Something went wrong", message, onRetry, testId = "error-state" }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-border bg-card p-10 text-center" data-testid={testId}>
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10 text-destructive">
        <AlertTriangle className="h-6 w-6" strokeWidth={1.5} />
      </div>
      <h3 className="mb-1 text-lg font-semibold">{title}</h3>
      <p className="mb-5 max-w-md text-sm text-muted-foreground">
        {message || "We couldn't load this data right now. Please try again in a moment."}
      </p>
      {onRetry && (
        <Button variant="outline" onClick={onRetry} data-testid="error-retry-btn">
          <RefreshCw className="mr-2 h-4 w-4" strokeWidth={1.5} /> Retry
        </Button>
      )}
    </div>
  );
}
