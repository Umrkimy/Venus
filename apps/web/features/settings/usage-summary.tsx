"use client";

import { useQuery } from "@tanstack/react-query";

import { getJson } from "@/lib/get-json";

type UsageTotal = {
  input_tokens: number;
  cached_tokens: number;
  output_tokens: number;
  cost_usd: number;
  // Models Core has no price for, so cost_usd leaves them out.
  unpriced_models: string[];
};

type UsageResponse = {
  today: UsageTotal;
  month: UsageTotal;
  all_time: UsageTotal;
};

const PERIODS: { key: keyof UsageResponse; label: string }[] = [
  { key: "today", label: "Today" },
  { key: "month", label: "This month" },
  { key: "all_time", label: "All time" },
];

const TOKENS = new Intl.NumberFormat("en", { notation: "compact" });

// One chat turn costs a fraction of a cent, so small amounts keep 4 decimals.
function dollars(amount: number): string {
  if (amount === 0) return "$0.00";
  return `$${amount.toFixed(amount < 1 ? 4 : 2)}`;
}

export default function UsageSummary() {
  const usage = useQuery({
    queryKey: ["usage"],
    queryFn: () => getJson<UsageResponse>("/api/usage"),
  });

  if (usage.isPending) {
    return (
      <div role="status">
        <span className="sr-only">Loading usage</span>
        <div className="h-16 w-full rounded-md bg-foreground/20 motion-safe:animate-pulse" />
      </div>
    );
  }

  if (usage.isError) {
    return (
      <p role="alert" className="text-sm text-destructive">
        Can&apos;t load the usage.
      </p>
    );
  }

  const unpriced = usage.data.all_time.unpriced_models;

  return (
    <div className="space-y-3">
      <dl className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {PERIODS.map(({ key, label }) => {
          const total = usage.data[key];
          return (
            <div key={key} className="rounded-lg border border-border p-3">
              <dt className="text-sm text-muted-foreground">{label}</dt>
              <dd className="mt-1 text-xl font-semibold tabular-nums">
                {dollars(total.cost_usd)}
              </dd>
              <dd className="text-xs text-muted-foreground tabular-nums">
                {TOKENS.format(total.input_tokens)} in (
                {TOKENS.format(total.cached_tokens)} cached),{" "}
                {TOKENS.format(total.output_tokens)} out
              </dd>
            </div>
          );
        })}
      </dl>
      {unpriced.length > 0 && (
        <p className="text-sm text-muted-foreground">
          No price known for {unpriced.join(", ")}: its tokens are counted but
          not in the dollars.
        </p>
      )}
    </div>
  );
}
