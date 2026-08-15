import { useEffect, useRef, useState } from "react";
import type { SockratesMood } from "./components/Sockrates";
import type { Message } from "./types";

const TALK_MS = 1200;
const IMPRESSED_MS = 900;
const HINT_MS = 1400;

/**
 * Derives Sockrates' mood from the state the chat already tracks.
 *
 * Only the two transient reactions are stored. `thinking`, `listening` and `idle`
 * are computed at render from props, which removes by construction the whole
 * class of bugs where a stored mood drifts out of sync with `busy`.
 */
export function useSockratesMood(
  messages: Message[],
  busy: boolean,
  hintBusy: boolean,
  hintCount: number,
  draft: string,
): SockratesMood {
  const [transient, setTransient] = useState<SockratesMood | null>(null);
  const seenMessages = useRef(0);
  const seenHints = useRef(hintCount);

  useEffect(() => {
    // App.handleSend rebuilds the array as [...prev.slice(0, -1), student, tutor],
    // so identity changes on every response and length is the only reliable signal.
    // The real sequence per turn is 0 -> 1 (optimistic student append) -> 2
    // (student replaced, tutor appended), which yields impressed then talking.
    if (messages.length <= seenMessages.current) {
      seenMessages.current = messages.length;
      return;
    }
    seenMessages.current = messages.length;

    const gainedTutorReply = messages[messages.length - 1]?.role === "tutor";
    // Scan back for the newest student message rather than slicing off the newly
    // added tail. App.handleSend REPLACES the optimistic student entry in place to
    // attach its anchor excerpt, so by the time the reply lands that message sits
    // below the slice index and a tail slice never sees it.
    let studentAsked = false;
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "student") {
        studentAsked = messages[i].text.trim().endsWith("?");
        break;
      }
    }

    // `impressed` has to lead into `talking` rather than compete with it. On its
    // own it is unreachable: the optimistic student append happens while `busy` is
    // still true, so the reaction is masked, and the reply then replaces it.
    const sequence: SockratesMood[] = gainedTutorReply
      ? studentAsked
        ? ["impressed", "talking"]
        : ["talking"]
      : studentAsked
        ? ["impressed"]
        : [];
    if (sequence.length === 0) return;

    let cancelled = false;
    let timer = 0;
    const play = (index: number) => {
      if (cancelled) return;
      if (index >= sequence.length) {
        setTransient(null);
        return;
      }
      const mood = sequence[index];
      setTransient(mood);
      timer = window.setTimeout(() => play(index + 1), mood === "talking" ? TALK_MS : IMPRESSED_MS);
    };
    play(0);

    // Covers both a new message arriving mid-sequence and unmount when App swaps
    // the whole chat out for the completion screen.
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [messages]);

  useEffect(() => {
    if (hintCount <= seenHints.current) {
      seenHints.current = hintCount;
      return;
    }
    seenHints.current = hintCount;
    setTransient("hinting");
    const timer = window.setTimeout(() => setTransient(null), HINT_MS);
    return () => window.clearTimeout(timer);
  }, [hintCount]);

  // What is actually happening always outranks a leftover reaction.
  if (busy || hintBusy) return "thinking";
  if (transient) return transient;
  if (draft.trim().length > 0) return "listening";
  return "idle";
}
