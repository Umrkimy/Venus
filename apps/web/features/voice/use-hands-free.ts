"use client";

import { useEffect, useRef, useState } from "react";

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

// ChatGPT-style voice in the browser: the mic stays open, a sentence starts
// when you talk and ends when you go quiet, then it's typed in for you.
export function useHandsFree({ enabled, busy, onHeard, onStop }: Options) {
  const [phase, setPhase] = useState<HandsFreePhase>("off");
  const [error, setError] = useState<string | null>(null);
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

    async function start() {
      try {
        // The browser's echo cancelling keeps most of Luna's voice out of the mic.
        stream = await navigator.mediaDevices.getUserMedia({
          audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
        });
      } catch {
        setError("Venus can't use your mic. Allow it in the browser's address bar.");
        return;
      }
      if (closed) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
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
            const ending = endingOf(text);
            if (ending === "stop") {
              stopRef.current();
            } else if (!busyRef.current) {
              heardRef.current(text);
              // "Goodbye": Luna says bye back, and hands-free turns off.
              if (ending === "bye") setListenOn(false);
            }
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
        if (now - lastLoudAt > END_SILENCE_MS || now - startedAt > MAX_RECORDING_MS) finish();
      }, TICK_MS);
    }

    void start();
    return () => {
      closed = true;
      window.clearInterval(timer);
      // Stopping the tracks turns the browser's mic light off.
      stream?.getTracks().forEach((track) => track.stop());
      void context?.close();
      setListeningActive(false);
      setPhase("off");
    };
  }, [enabled]);

  return { phase: enabled ? phase : "off", error: enabled ? error : null };
}
