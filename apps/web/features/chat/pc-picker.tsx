"use client";

import { Monitor } from "lucide-react";
import { useState } from "react";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useDevices, type Device } from "@/features/devices/use-devices";

// Remembered per browser: the phone and the PC can each pick their own.
const STORAGE_KEY = "venus-chat-pc";

function readChoice(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

// Which PC runs what you ask in chat: your last pick while it's online,
// else the main PC, else whichever PC is online.
export function usePcTarget() {
  const devices = useDevices();
  const [chosen, setChosen] = useState<string | null>(readChoice);

  const online = (devices.data ?? []).filter(
    (device): device is Device & { device_id: string } =>
      device.connected && device.device_id !== null,
  );
  const target =
    online.find((device) => device.device_id === chosen) ??
    online.find((device) => device.main) ??
    online[0];

  function choose(deviceId: string) {
    setChosen(deviceId);
    try {
      localStorage.setItem(STORAGE_KEY, deviceId);
    } catch {
      // Private mode: the pick lasts until the page closes.
    }
  }

  return { online, deviceId: target?.device_id, choose };
}

type PcPickerProps = ReturnType<typeof usePcTarget>;

// Only worth showing with two or more PCs online.
export default function PcPicker({ online, deviceId, choose }: PcPickerProps) {
  if (online.length < 2 || !deviceId) return null;
  return (
    <Select value={deviceId} onValueChange={choose}>
      <SelectTrigger
        aria-label="PC that runs your commands"
        className="h-9 max-w-36 gap-1.5 rounded-full border-none bg-transparent px-2.5 text-xs shadow-none"
      >
        <Monitor className="size-3.5 shrink-0" />
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {online.map((device) => (
          <SelectItem key={device.device_id} value={device.device_id}>
            {device.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
