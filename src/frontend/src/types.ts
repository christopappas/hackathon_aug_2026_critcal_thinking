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
}

export interface AccessProfile {
  dyslexia_support: boolean;
}

export interface SessionResponse {
  session_id: string;
  content: Content;
  min_turns: number;
  max_turns: number;
  opening_prompt: string;
  llm_enabled: boolean;
  access_profile: AccessProfile;
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
