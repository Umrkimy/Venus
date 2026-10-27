"use client";

import { useQuery } from "@tanstack/react-query";
import { AirVent, Clapperboard, Lightbulb, Monitor, Plug, Plus, Trash2, Tv } from "lucide-react";
import { useId, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { FIELD_HOVER, LABEL_CLASS, SELECT_TRIGGER_CLASS } from "@/features/settings/field-styles";
import { errorText } from "@/lib/error-text";
import { getJson } from "@/lib/get-json";

type Kind = "light" | "plug" | "tv" | "pc";
// Air-con and scenes only come from Home Assistant.
type DeviceKind = Kind | "aircon" | "scene";

type HomeDevice = {
  id: string;
  name: string;
  kind: DeviceKind;
  address: string | null;
  mac: string | null;
  tuya_id: string | null;
  tuya_version: number;
  has_key: boolean;
  ha_entity_id: string | null;
};

const KINDS: { value: Kind; label: string; examples: (name: string) => string }[] = [
  {
    value: "light",
    label: "Light (Tuya / Smart Life)",
    examples: (name) => `turn off the ${name}, ${name} 30%, make the ${name} blue`,
  },
  { value: "plug", label: "Plug (Tuya / Smart Life)", examples: (name) => `turn on the ${name}` },
  { value: "tv", label: "TV (Google / Android TV)", examples: (name) => `${name} volume 20, mute the ${name}` },
  { value: "pc", label: "Another PC to wake", examples: (name) => `wake the ${name}` },
];

const ICONS = { light: Lightbulb, plug: Plug, tv: Tv, pc: Monitor, aircon: AirVent, scene: Clapperboard };

function describe(device: HomeDevice) {
  if (device.ha_entity_id) return `Home Assistant · ${device.ha_entity_id}`;
  if (device.kind === "pc") return device.mac;
  if (device.kind === "tv") return device.address;
  return `${device.address} · Tuya ${device.tuya_version}${device.has_key ? "" : " · no key"}`;
}

// Settings, Home: the lights, plugs, TV and PCs Venus can control.
export default function HomeDevices() {
  const ids = useId();
  const [kind, setKind] = useState<Kind>("light");
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [mac, setMac] = useState("");
  const [tuyaId, setTuyaId] = useState("");
  const [localKey, setLocalKey] = useState("");
  const [version, setVersion] = useState("3.3");
  const [busy, setBusy] = useState(false);
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const devices = useQuery({
    queryKey: ["home-devices"],
    queryFn: () => getJson<HomeDevice[]>("/api/home/devices"),
  });
  const tuya = kind === "light" || kind === "plug";

  async function add(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    const body = {
      name: name.trim(),
      kind,
      address: kind === "pc" ? null : address.trim() || null,
      mac: kind === "pc" ? mac.trim() || null : null,
      tuya_id: tuya ? tuyaId.trim() || null : null,
      local_key: tuya ? localKey.trim() || null : null,
      tuya_version: Number(version),
    };
    try {
      const response = await fetch("/api/home/devices", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await response.json();
      if (!response.ok) {
        setError(errorText(data, "Check the fields."));
        return;
      }
      setName("");
      setAddress("");
      setMac("");
      setTuyaId("");
      setLocalKey("");
      setNotice(`Added ${data.name}. Try: ${KINDS.find((k) => k.value === kind)?.examples(data.name)}`);
      await devices.refetch();
    } catch {
      setError("Can't reach Venus. Is it running?");
    } finally {
      setBusy(false);
    }
  }

  async function remove(device: HomeDevice) {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`/api/home/devices/${device.id}`, { method: "DELETE" });
      if (!response.ok) setError(`Couldn't remove ${device.name}.`);
      await devices.refetch();
    } catch {
      setError("Can't reach Venus. Is it running?");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      {devices.isPending && (
        <div role="status">
          <span className="sr-only">Loading devices</span>
          <div className="h-12 w-full rounded-md bg-foreground/20 motion-safe:animate-pulse" />
        </div>
      )}
      {devices.isError && (
        <p role="alert" className="text-sm text-destructive">
          Can&apos;t load your devices.
        </p>
      )}
      {devices.isSuccess && devices.data.length === 0 && (
        <p className="text-sm text-muted-foreground">
          No devices yet. &quot;Volume up&quot; and &quot;lock my pc&quot; work without any.
        </p>
      )}
      {devices.isSuccess && devices.data.length > 0 && (
        <ul className="space-y-2">
          {devices.data.map((device) => {
            const Icon = ICONS[device.kind];
            return (
              <li
                key={device.id}
                className="flex items-center gap-3 rounded-lg border border-border px-4 py-3 hover:border-foreground/30 hover:bg-muted/60"
              >
                <Icon className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium">{device.name}</p>
                  <p className="truncate text-xs text-muted-foreground">{describe(device)}</p>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon-sm"
                  disabled={busy}
                  onClick={() => remove(device)}
                  aria-label={`Remove ${device.name}`}
                >
                  <Trash2 />
                </Button>
              </li>
            );
          })}
        </ul>
      )}

      {!adding && (
        <Button type="button" variant="outline" size="sm" className="mt-4" onClick={() => setAdding(true)}>
          <Plus />
          Add a device by hand
        </Button>
      )}
      {adding && (
        <form onSubmit={add} className="mt-5 space-y-4 border-t border-border pt-5">
          <div className="flex items-center">
            <p className="text-sm font-semibold">Add a device by hand</p>
            <Button type="button" variant="ghost" size="sm" className="ml-auto" onClick={() => setAdding(false)}>
              Cancel
            </Button>
          </div>
          <div>
            <label htmlFor={`${ids}-kind`} className={LABEL_CLASS}>
              Type
            </label>
            <Select value={kind} onValueChange={(value) => setKind(value as Kind)}>
              <SelectTrigger id={`${ids}-kind`} className={SELECT_TRIGGER_CLASS}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {KINDS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <label className={LABEL_CLASS}>
            Name (what you say)
            <Input
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder={kind === "tv" ? "tv" : kind === "pc" ? "laptop" : kind === "plug" ? "fan" : "bedroom light"}
              maxLength={40}
              autoComplete="off"
              className={FIELD_HOVER}
            />
          </label>
          {kind === "pc" ? (
            <label className={LABEL_CLASS}>
              MAC address
              <Input
                value={mac}
                onChange={(event) => setMac(event.target.value)}
                placeholder="AA:BB:CC:DD:EE:FF"
                autoComplete="off"
                className={FIELD_HOVER}
              />
              <span className="mt-1 block text-xs font-normal text-muted-foreground">
                Turn on Wake-on-LAN in that PC&apos;s BIOS and network card settings.
              </span>
            </label>
          ) : (
            <label className={LABEL_CLASS}>
              IP address on your home Wi-Fi
              <Input
                value={address}
                onChange={(event) => setAddress(event.target.value)}
                placeholder="192.168.1.40"
                autoComplete="off"
                className={FIELD_HOVER}
              />
              <span className="mt-1 block text-xs font-normal text-muted-foreground">
                Give it a fixed address in your router, so it doesn&apos;t change.
              </span>
            </label>
          )}
          {tuya && (
            <>
              <label className={LABEL_CLASS}>
                Tuya device id
                <Input
                  value={tuyaId}
                  onChange={(event) => setTuyaId(event.target.value)}
                  autoComplete="off"
                  className={FIELD_HOVER}
                />
              </label>
              <label className={LABEL_CLASS}>
                Local key
                <Input
                  type="password"
                  value={localKey}
                  onChange={(event) => setLocalKey(event.target.value)}
                  autoComplete="off"
                  className={FIELD_HOVER}
                />
                <span className="mt-1 block text-xs font-normal text-muted-foreground">
                  Saved encrypted. The home control guide shows how to get the id and key.
                </span>
              </label>
              <label className={LABEL_CLASS}>
                Protocol version
                <Input
                  value={version}
                  onChange={(event) => setVersion(event.target.value)}
                  inputMode="decimal"
                  className={FIELD_HOVER}
                />
              </label>
            </>
          )}
          <div className="flex items-center gap-3">
            <Button type="submit" disabled={busy || !name.trim()}>
              Add
            </Button>
            <p aria-live="polite" className="text-sm">
              {error && <span className="text-destructive">{error}</span>}
              {notice && <span className="text-muted-foreground">{notice}</span>}
            </p>
          </div>
        </form>
      )}
    </div>
  );
}
