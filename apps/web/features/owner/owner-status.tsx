import type { OwnerState } from "@/lib/use-owner";

// The loading bar and "can't reach Core" message every owner page shows.
export default function OwnerStatus({ owner }: { owner: OwnerState }) {
  if (owner.status === "loading") {
    return (
      <div role="status" className="mt-4">
        <span className="sr-only">Loading</span>
        <div className="h-5 w-40 rounded-md bg-muted/20 motion-safe:animate-pulse" />
      </div>
    );
  }
  if (owner.status === "unreachable") {
    return (
      <p role="alert" className="mt-4 text-sm text-danger">
        Can&apos;t reach Venus Core. Is it running?
      </p>
    );
  }
  return null;
}
