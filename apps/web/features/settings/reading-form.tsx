"use client";

import { useId } from "react";

import { saveReading, useReadingSettings } from "@/features/chat/reading-settings";
import TypedText from "@/features/chat/typed-text";

import { LABEL_CLASS } from "./field-styles";

const PREVIEW = "Hey, you're back. This is how fast my words come out when I'm not talking.";

const SLIDER_CLASS = "mt-2 w-full accent-primary";

// Like a visual novel's preferences: saved in this browser, changes apply at once.
export default function ReadingForm() {
  const reading = useReadingSettings();
  const speedId = useId();
  const volumeId = useId();
  const instantId = useId();

  return (
    <div className="space-y-5">
      <div>
        <label htmlFor={speedId} className={LABEL_CLASS}>
          Text speed
          <span className="ml-2 font-normal text-muted-foreground">
            {reading.textSpeed} letters a second
          </span>
        </label>
        <input
          id={speedId}
          type="range"
          min={10}
          max={100}
          step={5}
          value={reading.textSpeed}
          onChange={(event) => saveReading({ textSpeed: Number(event.target.value) })}
          disabled={reading.instantText}
          className={SLIDER_CLASS}
        />
        {/* Types again whenever the speed changes, so you see the new pace. */}
        <p className="mt-2 min-h-10 rounded-lg bg-muted/50 px-3 py-2 text-sm">
          <TypedText
            text={PREVIEW}
            reveal="type"
            said={null}
            speed={reading.textSpeed}
            instant={reading.instantText}
          />
        </p>
      </div>

      <div>
        <label htmlFor={volumeId} className={LABEL_CLASS}>
          Voice volume
          <span className="ml-2 font-normal text-muted-foreground">
            {Math.round(reading.volume * 100)}%
          </span>
        </label>
        <input
          id={volumeId}
          type="range"
          min={0}
          max={100}
          step={5}
          value={Math.round(reading.volume * 100)}
          onChange={(event) => saveReading({ volume: Number(event.target.value) / 100 })}
          className={SLIDER_CLASS}
        />
      </div>

      <div className="flex items-start gap-2.5">
        <input
          id={instantId}
          type="checkbox"
          checked={reading.instantText}
          onChange={(event) => saveReading({ instantText: event.target.checked })}
          className="mt-0.5 size-4 accent-primary"
        />
        <label htmlFor={instantId} className="text-sm">
          <span className="font-medium">Instant text</span>
          <span className="block text-muted-foreground">
            Show Venus&apos;s replies all at once instead of typing them out.
          </span>
        </label>
      </div>
    </div>
  );
}
