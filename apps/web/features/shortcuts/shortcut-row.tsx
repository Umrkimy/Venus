import { Pencil, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

import type { Shortcut } from "./shortcuts";

type ShortcutRowProps = {
  shortcut: Shortcut;
  editing: boolean;
  disabled: boolean;
  onEdit: (shortcut: Shortcut) => void;
  onDelete: (keyword: string) => void;
};

export default function ShortcutRow({
  shortcut,
  editing,
  disabled,
  onEdit,
  onDelete,
}: ShortcutRowProps) {
  return (
    <li
      className={`group flex items-start justify-between gap-3 rounded-lg border px-4 py-3 transition-colors ${
        editing
          ? "border-primary bg-primary/5"
          : "border-border hover:border-foreground/30 hover:bg-muted/60"
      }`}
    >
      <div className="min-w-0">
        <p className="font-medium">
          <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-sm">
            {shortcut.keyword}
          </span>{" "}
          <span className="font-normal text-muted-foreground">{shortcut.label}</span>
        </p>
        <p className="mt-1 break-all text-xs text-muted-foreground">{shortcut.home_url}</p>
        {shortcut.search_url && (
          <p className="break-all text-xs text-muted-foreground">{shortcut.search_url}</p>
        )}
      </div>
      {/* Faded until the row is hovered or focused, always visible on touch. */}
      <div className="flex shrink-0 gap-1 transition-opacity md:opacity-60 md:group-hover:opacity-100 md:group-focus-within:opacity-100">
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              disabled={disabled}
              onClick={() => onEdit(shortcut)}
              aria-label={`Edit ${shortcut.keyword}`}
              className="hover:text-primary"
            >
              <Pencil />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Edit</TooltipContent>
        </Tooltip>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              disabled={disabled}
              onClick={() => onDelete(shortcut.keyword)}
              aria-label={`Delete ${shortcut.keyword}`}
              className="hover:bg-destructive/10 hover:text-destructive"
            >
              <Trash2 />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Delete</TooltipContent>
        </Tooltip>
      </div>
    </li>
  );
}
