"use client";

import { Ban, Trash2 } from "lucide-react";
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
import { cn } from "@/lib/utils";

import AddDevice from "./add-device";
import { type Device, useDeviceActions, useDevices } from "./use-devices";

function statusLine(device: Device) {
  if (device.revoked_at) return "Revoked";
  if (device.connected) return "Connected";
  if (device.last_seen_at)
    return `Last seen ${new Date(device.last_seen_at).toLocaleString()}`;
  return "Never connected";
}

export default function DeviceList() {
  const devices = useDevices();
  const actions = useDeviceActions();
  const [revoking, setRevoking] = useState<Device | null>(null);

  async function revoke() {
    const device = revoking;
    setRevoking(null);
    if (device) await actions.revoke(device.id);
  }

  if (devices.isPending) {
    return (
      <div role="status">
        <span className="sr-only">Loading devices</span>
        <div className="h-24 rounded-lg bg-foreground/10 motion-safe:animate-pulse" />
      </div>
    );
  }

  if (devices.isError) {
    return (
      <p role="alert" className="text-sm text-destructive">
        Can&apos;t load devices.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <AddDevice onAdd={actions.create} />
      {actions.error && (
        <p role="alert" className="text-sm text-destructive">
          {actions.error}
        </p>
      )}
      {devices.data.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No devices yet. Your main PC shows up the first time Venus starts on
          it.
        </p>
      ) : (
        <ul className="space-y-2">
          {devices.data.map((device) => (
            <li
              key={device.id}
              className="flex items-start gap-2 rounded-lg border border-border p-3"
            >
              <div
                className={cn(
                  "min-w-0 flex-1",
                  device.revoked_at && "opacity-60",
                )}
              >
                <p className="text-sm font-medium break-words">
                  {device.name}
                  {device.main && (
                    <Badge variant="secondary" className="ml-2">
                      Main
                    </Badge>
                  )}
                  {device.device_id && (
                    <span className="ml-2 font-normal text-muted-foreground">
                      {device.device_id}
                    </span>
                  )}
                </p>
                <p className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
                  {device.connected && (
                    <span
                      aria-hidden
                      className="size-1.5 rounded-full bg-emerald-500"
                    />
                  )}
                  {statusLine(device)}
                </p>
              </div>
              {!device.revoked_at && !device.main && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setRevoking(device)}
                  className="text-muted-foreground hover:text-destructive"
                >
                  <Ban />
                  Revoke
                </Button>
              )}
              {device.revoked_at && (
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label={`Delete ${device.name}`}
                  onClick={() => actions.remove(device.id)}
                  className="text-muted-foreground hover:text-destructive"
                >
                  <Trash2 />
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}
      <AlertDialog
        open={revoking !== null}
        onOpenChange={(open) => {
          if (!open) setRevoking(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Revoke {revoking?.name}?</AlertDialogTitle>
            <AlertDialogDescription>
              It disconnects now and its token stops working for good. To use
              that PC again, add it as a new device.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={revoke}>
              Revoke
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
