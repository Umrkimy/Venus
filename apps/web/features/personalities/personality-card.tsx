"use client";

import { Pencil, Trash2 } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

import PersonalityEditor from "./personality-editor";
import type { Personality, usePersonalityActions } from "./use-personalities";

type PersonalityCardProps = {
  personality: Personality;
  actions: ReturnType<typeof usePersonalityActions>;
  onDelete: (personality: Personality) => void;
};

// Shows one personality; Edit turns the same card into the editor.
export default function PersonalityCard({
  personality,
  actions,
  onDelete,
}: PersonalityCardProps) {
  const [editing, setEditing] = useState(false);

  async function save(name: string, text: string) {
    const saved = await actions.update(personality.id, name, text);
    if (saved) setEditing(false);
    return saved;
  }

  return (
    <li className="rounded-lg border border-border p-4">
      {editing ? (
        <PersonalityEditor
          initialName={personality.name}
          initialText={personality.text}
          onSave={save}
          onCancel={() => setEditing(false)}
        />
      ) : (
        <>
          <div className="flex items-center gap-2">
            <h3 className="min-w-0 truncate font-medium">{personality.name}</h3>
            {personality.active && <Badge>Active</Badge>}
          </div>
          <p className="mt-1 line-clamp-2 text-sm whitespace-pre-line text-muted-foreground">
            {personality.text || "No text yet."}
          </p>
          <div className="mt-3 flex items-center gap-1">
            {!personality.active && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => actions.activate(personality.id)}
              >
                Use this
              </Button>
            )}
            <Button variant="ghost" size="sm" onClick={() => setEditing(true)}>
              <Pencil />
              Edit
            </Button>
            {/* The active one can't be deleted, so its button isn't offered. */}
            {!personality.active && (
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label={`Delete ${personality.name}`}
                onClick={() => onDelete(personality)}
                className="ml-auto text-muted-foreground hover:text-destructive"
              >
                <Trash2 />
              </Button>
            )}
          </div>
        </>
      )}
    </li>
  );
}
