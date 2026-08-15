export type AnchorKind = "text" | "region" | "temporal";

export interface Anchor {
  kind: AnchorKind;
  quote?: string;
  start?: number;
  end?: number;
  region_id?: string;
  box?: number[];
  timestamp_s?: number;
}

export interface ChartRegion {
  id: string;
  box: [number, number, number, number];
  caption: string;
}

export interface TranscriptLine {
  t: number;
  text: string;
}

export interface Content {
  id: string;
  title: string;
  subject?: string;
  blurb?: string;
  grade_level?: number;
  intro: string;
  body: string;
  chart: { asset_url: string; alt: string; regions: ChartRegion[] };
  video: { asset_url: string | null; transcript: TranscriptLine[] };
  opening_prompt: string;
}

export interface ContentSummary {
  id: string;
  title: string;
  subject: string;
  blurb: string;
  grade_level: number | null;
  icon?: string | null;
  generated?: boolean;
}

export interface Template {
  id: string;
  name: string;
  description: string;
  icon: string;
  trap: string;
  subject: string;
  chart_kind: "bar" | "scatter";
  generation_instructions: string;
  builtin: boolean;
}

export interface GenerateRequest {
  template_id: string;
  topic: string;
  extra_instructions?: string;
  source_text?: string;
  grade_level?: number;
  generation_instructions?: string;
}

/** A generated piece carries the teacher-only fields the student payload never shows. */
export interface GeneratedContent extends Content {
  icon?: string;
  review_status: "draft" | "published";
  thinking_trap?: string;
  source?: {
    template_id?: string;
    topic?: string;
    generated_with_llm?: boolean;
    created_at?: string;
  };
}

export interface GenerateResponse {
  content: GeneratedContent;
  warnings: string[];
  thinking_trap: string;
  generated_with_llm: boolean;
}

export interface TeacherContentRow {
  id: string;
  title: string;
  subject: string;
  blurb: string;
  icon: string | null;
  grade_level: number | null;
  generated: boolean;
  review_status: "draft" | "published";
  thinking_trap: string;
  source: { topic?: string; generated_with_llm?: boolean; created_at?: string };
}

export interface AccessProfile {
  dyslexia_support: boolean;
}

export type LlmMode = "live" | "stub";

export interface LlmModeResponse {
  llm_mode: LlmMode;
  llm_enabled: boolean;
  model: string;
}

export interface HealthResponse {
  status: string;
  llm_enabled: boolean;
  model: string;
}

export interface SessionResponse {
  session_id: string;
  content: Content;
  min_turns: number;
  max_turns: number;
  opening_prompt: string;
  llm_enabled: boolean;
  access_profile: AccessProfile;
  llm_mode: LlmMode;
}

export interface ChatResponse {
  reply: string;
  turns_used: number;
  turns_remaining: number;
  status: string;
  is_complete: boolean;
  anchor_excerpt: string | null;
}

export interface DimensionScore {
  dimension: string;
  name: string;
  score: number;
  evidence_quote: string;
  feedback: string;
}

export interface Report {
  session_id: string;
  overall_score: number;
  bloom_level_reached: string;
  explanation: string;
  dimensions: DimensionScore[];
  next_step: string;
  generated_with_llm: boolean;
  accommodations: string[];
}

export interface Message {
  role: "student" | "tutor";
  text: string;
  anchorExcerpt?: string | null;
}

export interface HintResponse {
  hint: string;
  hint_level: number;
  hints_used_this_turn: number;
  max_hints_per_turn: number;
}

export interface ExploreMessage {
  role: "student" | "tutor";
  text: string;
}

export interface ExploreStartResponse {
  opening: string;
  anchor_excerpt: string | null;
  max_messages: number;
}

export interface ExploreMessageResponse {
  reply: string;
  messages_used: number;
  max_messages: number;
}
