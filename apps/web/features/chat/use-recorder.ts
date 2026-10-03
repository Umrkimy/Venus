"use client";

import { useEffect, useRef, useState } from "react";

export type RecorderState = "idle" | "recording" | "transcribing";

// The browser says why the microphone failed; turn that into a next step.
function micProblem(problem: unknown): string {
  const name = problem instanceof DOMException ? problem.name : "";
  if (name === "NotAllowedError") {
    return "Microphone is blocked. Allow it in the address bar's site settings.";
  }
  if (name === "NotFoundError") return "No microphone found.";
  if (name === "NotReadableError") return "Another app is using the microphone.";
  if (!navigator.mediaDevices) return "This page can't use a microphone (needs localhost or https).";
  return `Venus can't use your microphone${name ? ` (${name})` : ""}.`;
}

// Records from the microphone, then asks Core to turn it into text.
export function useRecorder(onText: (text: string) => void) {
  const [state, setState] = useState<RecorderState>("idle");
  const [error, setError] = useState<string | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);

  // Let go of the microphone if the page closes mid-recording.
  useEffect(() => {
    return () => {
      recorderRef.current?.stream.getTracks().forEach((track) => track.stop());
    };
  }, []);

  async function send(audio: Blob) {
    setState("transcribing");
    try {
      const response = await fetch("/api/voice/transcribe", {
        method: "POST",
        headers: { "Content-Type": audio.type || "audio/webm" },
        body: audio,
      });
      if (!response.ok) {
        // e.g. "Voice needs an OpenAI API key": Core's words say what to do.
        const data = await response.json().catch(() => null);
        setError(data?.detail ?? "Couldn't hear that.");
        return;
      }
      const data: { text: string } = await response.json();
      if (data.text) onText(data.text);
      else setError("Didn't catch anything. Try again?");
    } catch {
      setError("Can't reach Venus Core. Is it running?");
    } finally {
      setState("idle");
    }
  }

  async function start() {
    setError(null);
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (problem) {
      // Blocked, no microphone, or not on localhost / https.
      setError(micProblem(problem));
      return;
    }
    const recorder = new MediaRecorder(stream);
    const chunks: Blob[] = [];
    recorder.ondataavailable = (event) => chunks.push(event.data);
    recorder.onstop = () => {
      // Turns the browser's "in use" light off.
      stream.getTracks().forEach((track) => track.stop());
      recorderRef.current = null;
      void send(new Blob(chunks, { type: recorder.mimeType }));
    };
    recorderRef.current = recorder;
    recorder.start();
    setState("recording");
  }

  function stop() {
    recorderRef.current?.stop();
  }

  return { state, error, start, stop };
}
