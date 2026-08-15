import type {
  AccessProfile,
  Anchor,
  ChatResponse,
  ContentSummary,
  ExploreMessageResponse,
  ExploreStartResponse,
  GenerateRequest,
  GenerateResponse,
  GeneratedContent,
  HealthResponse,
  HintResponse,
  LlmMode,
  LlmModeResponse,
  Report,
  SessionResponse,
  TeacherContentRow,
  Template,
} from "./types";

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

export const fetchHealth = () => request<HealthResponse>("/health");

export const setSessionLlmMode = (sessionId: string, mode: LlmMode) =>
  request<LlmModeResponse>(`/session/${sessionId}/llm-mode`, {
    method: "PUT",
    body: JSON.stringify({ llm_mode: mode }),
  });

export const startSession = (
  contentId: string,
  accessProfile: AccessProfile,
  llmMode: LlmMode,
) =>
  request<SessionResponse>("/session", {
    method: "POST",
    body: JSON.stringify({
      content_id: contentId,
      access_profile: accessProfile,
      llm_mode: llmMode,
    }),
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

export const startExplore = (sessionId: string, anchor: Anchor) =>
  request<ExploreStartResponse>("/explore/start", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, anchor }),
  });

export const sendExploreMessage = (sessionId: string, message: string) =>
  request<ExploreMessageResponse>("/explore/message", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, message }),
  });

// --- Teacher portal ---

export const listTemplates = () => request<Template[]>("/teacher/templates");

export const generateContent = (body: GenerateRequest) =>
  request<GenerateResponse>("/teacher/generate", {
    method: "POST",
    body: JSON.stringify(body),
  });

export const importContent = (payload: unknown) =>
  request<GenerateResponse>("/teacher/import", {
    method: "POST",
    body: JSON.stringify({ payload }),
  });

export const fetchImportSchema = () => request<{ shape: string }>("/teacher/import/schema");

export const listTeacherContent = () => request<TeacherContentRow[]>("/teacher/content");

export const getTeacherContent = (id: string) =>
  request<GeneratedContent>(`/teacher/content/${id}`);

export const publishContent = (id: string) =>
  request<{ review_status: string }>(`/teacher/content/${id}/publish`, { method: "POST" });

export const unpublishContent = (id: string) =>
  request<{ review_status: string }>(`/teacher/content/${id}/unpublish`, { method: "POST" });

export const updateContent = (id: string, patch: Record<string, string>) =>
  request<GeneratedContent>(`/teacher/content/${id}`, {
    method: "PUT",
    body: JSON.stringify(patch),
  });

export const deleteContent = (id: string) =>
  request<{ deleted: string }>(`/teacher/content/${id}`, { method: "DELETE" });
