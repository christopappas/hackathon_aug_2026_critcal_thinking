import type { AccessProfile, Anchor, ChatResponse, ContentSummary, HintResponse, Report, SessionResponse } from "./types";

const BASE = "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status}: ${detail}`);
  }
  return response.json() as Promise<T>;
}

export const listContent = () => request<ContentSummary[]>("/content");

export const startSession = (contentId: string, accessProfile: AccessProfile) =>
  request<SessionResponse>("/session", {
    method: "POST",
    body: JSON.stringify({ content_id: contentId, access_profile: accessProfile }),
  });

export const sendMessage = (sessionId: string, message: string, anchor: Anchor | null) =>
  request<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, message, anchor }),
  });

export const fetchReport = (sessionId: string) =>
  request<Report>(`/report/${sessionId}`);

export const requestHint = (sessionId: string, anchor: Anchor | null) =>
  request<HintResponse>("/hint", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, anchor }),
  });
