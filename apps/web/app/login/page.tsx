"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

function messageForStatus(status: number): string {
  if (status === 401) return "Wrong username or password.";
  if (status === 422) return "Username or password is too long.";
  if (status === 429) return "Too many attempts. Try again in 15 minutes.";
  return "Can't reach Venus Core. Is it running?";
}

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setPending(true);

    const form = new FormData(event.currentTarget);
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: form.get("username"),
          password: form.get("password"),
        }),
      });
      if (response.ok) {
        router.push("/");
        return;
      }
      setError(messageForStatus(response.status));
    } catch {
      setError(messageForStatus(0));
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="mx-auto w-full max-w-sm px-4 pt-24">
      <h1 className="text-2xl font-semibold tracking-tight">
        Sign in to Venus
      </h1>

      <form onSubmit={handleSubmit} className="mt-8 flex flex-col gap-6">
        <div className="flex flex-col gap-2">
          <label htmlFor="username" className="text-sm font-medium">
            Username
          </label>
          <input
            id="username"
            name="username"
            autoComplete="username"
            required
            maxLength={100}
            className="rounded-md border border-border bg-transparent px-3 py-2 outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </div>

        <div className="flex flex-col gap-2">
          <label htmlFor="password" className="text-sm font-medium">
            Password
          </label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            maxLength={1024}
            className="rounded-md border border-border bg-transparent px-3 py-2 outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </div>

        <button
          type="submit"
          disabled={pending}
          className="rounded-md bg-primary px-4 py-2 font-medium text-primary-foreground disabled:opacity-60 motion-safe:transition-transform motion-safe:active:scale-[0.98]"
        >
          {pending ? "Signing in…" : "Sign in"}
        </button>

        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
      </form>
    </main>
  );
}
