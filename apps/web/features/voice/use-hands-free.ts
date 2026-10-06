"use client";

import { useEffect, useRef, useState } from "react";

import {
  joinResults,
  makeBrowserSpeech,
  markSpeechBroken,
  onlyFillers,
  pauseAfter,
} from "./browser-speech";
import { setListenOn, setListeningActive } from "./listen-store";
import { endingOf } from "./stop-phrases";

// How often the mic's loudness is checked (cheap: one small array per tick).
const TICK_MS = 50;
// Quiet this long after talking = you finished your sentence.
const END_SILENCE_MS = 800;
// Shorter than this is a cough or a click, not worth paying to transcribe.
const MIN_SPEECH_MS = 400;
const MAX_RECORDING_MS = 30_000;
// Loudness (0 to 1) that counts as talking: well above the room's own hum.
const MIN_START = 0.02;
const NOISE_TIMES = 3;

export type HandsFreePhase = "off" | "waiting" | "recording" | "transcribing";

type Options = {
  enabled: boolean;
  // Luna is answering or talking: only "stop" counts, so her voice leaking
  // into the mic can't become a new question.
  busy: boolean;
  onHeard: (text: string) => void;
  onStop: () => void;
};

function loudness(samples: Float32Array<ArrayBuffer>): number {
  let sum = 0;
  for (const sample of samples) sum += sample * sample;
  return Math.sqrt(sum / samples.length);
}

async function transcribe(audio: Blob): Promise<string> {
  const response = await fetch("/api/voice/transcribe", {
    method: "POST",
    headers: { "Content-Type": audio.type || "audio/webm" },
    body: audio,
  });
  // 422: Core heard only silence. Nothing to say, keep listening.
  if (!response.ok) return "";
  const data = await response.json();
  return typeof data.text === "string" ? data.text.trim() : "";
}

const MIC_BLOCKED =
  "Venus can't use your mic. Allow it in the browser's address bar.";

// ChatGPT-style voice in the browser: the mic stays open, a sentence starts
// when you talk and ends when you go quiet, then it's typed in for you.
// With the browser's own speech-to-text your words show while you talk;
// without it (Brave), the sentence is sent to Core once you stop.
export function useHandsFree({ enabled, busy, onHeard, onStop }: Options) {
  const [phase, setPhase] = useState<HandsFreePhase>("off");
  const [error, setError] = useState<string | null>(null);
  // Your words so far, while you're still talking (browser speech only).
  const [words, setWords] = useState("");
  // The interval reads these; refs so it always sees the latest.
  const busyRef = useRef(busy);
  const heardRef = useRef(onHeard);
  const stopRef = useRef(onStop);
  useEffect(() => {
    busyRef.current = busy;
    heardRef.current = onHeard;
    stopRef.current = onStop;
  });

  useEffect(() => {
    if (!enabled) return;
    let closed = false;
    let stream: MediaStream | null = null;
    let context: AudioContext | null = null;
    let timer = 0;
    let stopSpeech = () => {};

    // A whole sentence was heard, by the browser or by Core.
    function handle(text: string) {
      const ending = endingOf(text);
      if (ending === "stop") {
        stopRef.current();
      } else if (!busyRef.current) {
        heardRef.current(text);
        // "Goodbye": Luna says bye back, and hands-free turns off.
        if (ending === "bye") setListenOn(false);
      }
    }

    // The mic, opened once. Keeping it open also stops the iPhone asking
    // for permission again each time speech recognition restarts.
    async function openMic(): Promise<boolean> {
      if (stream) return true;
      try {
        // The browser's echo cancelling keeps most of Luna's voice out of the mic.
        stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
        });
      } catch {
        setError(MIC_BLOCKED);
        return false;
      }
      if (closed) {
        stream.getTracks().forEach((track) => track.stop());
        return false;
      }
      return true;
    }

    // True when the browser's speech-to-text took the job.
    function startBrowserSpeech(): boolean {
      const speech = makeBrowserSpeech();
      if (!speech) return false;
      // One recognizer runs the whole time (each restart can ask for the mic
      // again), so its text keeps growing: `used` is what was already sent.
      let full = "";
      let used = 0;
      let heard = "";
      let quiet = 0;
      let failed = false;

      // Quiet for a moment after words = you finished your sentence.
      const finish = () => {
        window.clearTimeout(quiet);
        const text = heard;
        heard = "";
        used = full.length;
        setWords("");
        setPhase("waiting");
        if (!onlyFillers(text)) handle(text);
      };
      speech.onresult = (event) => {
        full = joinResults(event.results);
        // The browser rewrote its earlier words: start counting again.
        if (full.length < used) used = 0;
        heard = full.slice(used).trim();
        if (!heard) return;
        // While Luna talks the mic hears her too; only "stop" counts then, so don't show it.
        if (!busyRef.current) {
          setWords(heard);
          setPhase("recording");
        }
        window.clearTimeout(quiet);
        quiet = window.setTimeout(finish, pauseAfter(heard));
      };
      speech.onerror = (event) => {
        if (event.error === "not-allowed") {
          closed = true;
          setError(MIC_BLOCKED);
        } else if (markSpeechBroken(event.error)) {
          failed = true;
        }
      };
      // The browser stops by itself after a pause or an error: start again.
      speech.onend = () => {
        // Words not sent yet still count; the next start begins empty.
        if (heard) finish();
        full = "";
        used = 0;
        if (closed) return;
        if (failed) {
          setWords("");
          void startRecorder();
          return;
        }
        try {
          speech.start();
        } catch {
          // Already starting; the next end tries again.
        }
      };
      stopSpeech = () => {
        window.clearTimeout(quiet);
        speech.abort();
      };
      setError(null);
      setListeningActive(true);
      setPhase("waiting");
      speech.start();
      return true;
    }

    async function start() {
      if (!(await openMic())) return;
      if (startBrowserSpeech()) return;
      await startRecorder();
    }

    async function startRecorder() {
      if (!(await openMic()) || !stream) return;
      setError(null);
      setListeningActive(true);
      setPhase("waiting");
      context = new AudioContext();
      const analyser = context.createAnalyser();
      analyser.fftSize = 1024;
      context.createMediaStreamSource(stream).connect(analyser);
      const samples = new Float32Array(analyser.fftSize);

      let noise = 0.005; // The room's hum, learned while nobody talks.
      let recorder: MediaRecorder | null = null;
      let chunks: Blob[] = [];
      let startedAt = 0;
      let lastLoudAt = 0;
      let loudMs = 0;
      let transcribing = false;

      const finish = () => {
        const done = recorder;
        recorder = null;
        if (!done) return;
        const spoke = loudMs;
        done.onstop = async () => {
          const audio = new Blob(chunks, { type: done.mimeType });
          chunks = [];
          if (closed || spoke < MIN_SPEECH_MS) {
            setPhase("waiting");
            return;
          }
          transcribing = true;
          setPhase("transcribing");
          try {
            const text = await transcribe(audio);
            if (closed || !text) return;
            handle(text);
          } catch {
            // Core unreachable for a moment: the next sentence tries again.
          } finally {
            transcribing = false;
            if (!closed) setPhase("waiting");
          }
        };
        done.stop();
      };

      timer = window.setInterval(() => {
        analyser.getFloatTimeDomainData(samples);
        const level = loudness(samples);
        const now = performance.now();
        const talking = level > Math.max(MIN_START, noise * NOISE_TIMES);
        if (!recorder) {
          if (!talking) {
            noise = 0.95 * noise + 0.05 * level;
            return;
          }
          if (transcribing || !stream) return; // One sentence at a time.
          recorder = new MediaRecorder(stream);
          chunks = [];
          recorder.ondataavailable = (event) => chunks.push(event.data);
          recorder.start();
          startedAt = lastLoudAt = now;
          loudMs = 0;
          setPhase("recording");
          return;
        }
        if (talking) {
          loudMs += TICK_MS;
          lastLoudAt = now;
        }
        if (
          now - lastLoudAt > END_SILENCE_MS ||
          now - startedAt > MAX_RECORDING_MS
        )
          finish();
      }, TICK_MS);
    }

    void start();
    return () => {
      closed = true;
      stopSpeech();
      window.clearInterval(timer);
      // Stopping the tracks turns the browser's mic light off.
      stream?.getTracks().forEach((track) => track.stop());
      void context?.close();
      setListeningActive(false);
      setPhase("off");
      setWords("");
    };
  }, [enabled]);

  return {
    phase: enabled ? phase : "off",
    error: enabled ? error : null,
    words: enabled ? words : "",
  };
}
