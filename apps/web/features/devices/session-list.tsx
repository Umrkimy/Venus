"use client";

import { LogOut } from "lucide-react";
import { useState } from "react";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

import { browserName } from "./browser-name";
import { useSessionActions, useSessions } from "./use-sessions";

export default function SessionList() {
  const sessions = useSessions();
  const actions = useSessionActions();
  const [confirmAll, setConfirmAll] = useState(false);

  if (sessions.isPending) {
    return (
      <div role="status">
        <span className="sr-only">Loading signed-in browsers</span>
        <div className="h-24 rounded-lg bg-foreground/10 motion-safe:animate-pulse" />
      </div>
    );
  }

  if (sessions.isError) {
    return (
      <p role="alert" className="text-sm text-destructive">
        Can&apos;t load signed-in browsers.
      </p>
    );
  }

  const others = sessions.data.filter((session) => !session.current);

  return (
    <div className="space-y-3">
      {actions.error && (
        <p role="alert" className="text-sm text-destructive">
          {actions.error}
        </p>
      )}
      <ul className="space-y-2">
        {sessions.data.map((session) => (
          <li
            key={session.id}
            className="flex items-start gap-2 rounded-lg border border-border p-3"
          >
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">
                {browserName(session.user_agent)}
                {session.current && (
                  <Badge variant="secondary" className="ml-2">
                    This browser
                  </Badge>
                )}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Signed in {new Date(session.created_at).toLocaleDateString()}
                {session.last_seen_at &&
                  ` · last active ${new Date(session.last_seen_at).toLocaleString()}`}
              </p>
            </div>
            {!session.current && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => actions.signOut(session.id)}
                className="text-muted-foreground hover:text-destructive"
              >
                <LogOut />
                Sign out
              </Button>
            )}
          </li>
        ))}
      </ul>
      {others.length > 0 && (
        <Button variant="outline" size="sm" onClick={() => setConfirmAll(true)}>
          Sign out all other browsers
        </Button>
      )}
      <AlertDialog open={confirmAll} onOpenChange={setConfirmAll}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Sign out {others.length} other browsers?
            </AlertDialogTitle>
            <AlertDialogDescription>
              Every login except this one ends now. Use it if you lost a phone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={actions.signOutOthers}
            >
              Sign out
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
