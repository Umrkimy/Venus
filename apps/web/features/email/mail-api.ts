import { errorText } from "@/lib/error-text";

export type Category = "primary" | "newsletters" | "promotions";
export type Summary = {
  uid: string;
  sender: string;
  sender_address: string;
  subject: string;
  date: string | null;
  unread: boolean;
  category: Category;
};
export type Message = Summary & { to: string[]; cc: string[]; body: string; html: string; attachments: string[] };

export async function load<T>(path: string): Promise<T> {
  const response = await fetch(path);
  const data = await response.json();
  if (!response.ok) throw new Error(errorText(data, "Couldn't load that."));
  return data as T;
}

export async function post<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(errorText(data, "That didn't work."));
  return data as T;
}

// The same list for the Email page and the home Today card, so they share one copy.
export function inboxQuery(accountId: string | null) {
  return {
    queryKey: ["email-inbox", accountId],
    queryFn: () => load<Summary[]>(`/api/email/accounts/${accountId}/messages`),
    enabled: accountId !== null,
    retry: false,
  };
}
