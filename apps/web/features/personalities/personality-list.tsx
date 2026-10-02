"use client";

import { Plus } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";

import DeletePersonalityDialog from "./delete-personality-dialog";
import PersonalityCard from "./personality-card";
import PersonalityEditor from "./personality-editor";
import {
  type Personality,
  usePersonalities,
  usePersonalityActions,
} from "./use-personalities";

export default function PersonalityList() {
  const personalities = usePersonalities();
  const actions = usePersonalityActions();
  const [adding, setAdding] = useState(false);
  const [deleting, setDeleting] = useState<Personality | null>(null);

  async function create(name: string, text: string) {
    const created = await actions.create(name, text);
    if (created) setAdding(false);
    return created !== null;
  }

  async function remove() {
    const personality = deleting;
    setDeleting(null);
    if (personality) await actions.remove(personality.id);
  }

  if (personalities.isPending) {
    return (
      <div role="status">
        <span className="sr-only">Loading personalities</span>
        <div className="h-24 rounded-lg bg-foreground/10 motion-safe:animate-pulse" />
      </div>
    );
  }

  if (personalities.isError) {
    return (
      <p role="alert" className="text-sm text-destructive">
        Can&apos;t load personalities.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {!adding && (
        <Button variant="outline" size="sm" onClick={() => setAdding(true)}>
          <Plus />
          New personality
        </Button>
      )}
      {actions.error && (
        <p role="alert" className="text-sm text-destructive">
          {actions.error}
        </p>
      )}
      <ul className="space-y-3">
        {adding && (
          <li className="rounded-lg border border-border p-4">
            <PersonalityEditor
              initialName=""
              initialText=""
              onSave={create}
              onCancel={() => setAdding(false)}
            />
          </li>
        )}
        {personalities.data.map((personality) => (
          <PersonalityCard
            key={personality.id}
            personality={personality}
            actions={actions}
            onDelete={setDeleting}
          />
        ))}
      </ul>
      <DeletePersonalityDialog
        personality={deleting}
        onCancel={() => setDeleting(null)}
        onConfirm={remove}
      />
    </div>
  );
}
