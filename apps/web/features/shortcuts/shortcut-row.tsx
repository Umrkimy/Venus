import type { Shortcut } from "./shortcuts";

type ShortcutRowProps = {
  shortcut: Shortcut;
  buttonClass: string;
  disabled: boolean;
  onEdit: (shortcut: Shortcut) => void;
  onDelete: (keyword: string) => void;
};

export default function ShortcutRow({
  shortcut,
  buttonClass,
  disabled,
  onEdit,
  onDelete,
}: ShortcutRowProps) {
  return (
    <li className="flex items-start justify-between gap-3 rounded-md border border-border px-4 py-3">
      <div className="min-w-0">
        <p className="font-medium">
          {shortcut.keyword}{" "}
          <span className="font-normal text-muted">{shortcut.label}</span>
        </p>
        <p className="break-all text-xs text-muted">{shortcut.home_url}</p>
        {shortcut.search_url && (
          <p className="break-all text-xs text-muted">{shortcut.search_url}</p>
        )}
      </div>
      <div className="flex shrink-0 gap-2">
        <button
          type="button"
          disabled={disabled}
          onClick={() => onEdit(shortcut)}
          className={buttonClass}
        >
          Edit
        </button>
        <button
          type="button"
          disabled={disabled}
          onClick={() => onDelete(shortcut.keyword)}
          className={buttonClass}
        >
          Delete
        </button>
      </div>
    </li>
  );
}
