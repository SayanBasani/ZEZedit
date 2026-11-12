export type ReviewStatus = 'recommended' | 'needs_review' | 'approved' | 'rejected';

export interface ScoreBreakdown {
  semantic_interest: number;
  narrative_completeness: number;
  conversation_structure: number;
  visual_interest: number;
  audio_evidence: number;
  opening_clarity: number;
  ending_completeness: number;
  duration_suitability: number;
  context_dependency_penalty: number;
  total_score: number;
  hook_strength?: number;
  dialogue_interest?: number;
  emotional_signal?: number;
  action_motion?: number;
  attractiveness_estimate?: number;
}

export interface GateResults {
  overall_status: ReviewStatus;
  minimum_score_pass: boolean;
  duration_pass: boolean;
  transcript_pass: boolean;
  narrative_pass: boolean;
  visual_pass: boolean;
  context_pass: boolean;
  failure_reasons: string[];
}

export interface CandidateItem {
  id: string;
  project_id: string;
  media_asset_id: string;
  analysis_run_id: string;
  job_id?: string | null;
  start_time: number;
  end_time: number;
  duration: number;
  suggested_start_time: number;
  suggested_end_time: number;
  is_user_modified: boolean;
  title: string;
  suggested_title: string;
  description: string;
  category: string;
  secondary_categories: string[];
  quality_score: number;
  score_breakdown: ScoreBreakdown;
  gate_results: GateResults;
  warnings: string[];
  missing_evidence: string[];
  review_status: ReviewStatus;
  rejection_reason?: string | null;
  transcript_references: string[];
  scene_references: string[];
  visual_evidence: Array<{ timestamp?: number; description?: string; category?: string }>;
  audio_evidence: Array<Record<string, unknown>>;
  ai_explanation: {
    hook?: string;
    why_it_works?: string;
    suggested_title?: string;
    target_audience?: string;
    strengths?: string[];
    risks?: string[];
    scoring_version?: string;
    provider?: string;
  };
  alternative_of_candidate_id?: string | null;
  overlap_group_id?: string | null;
  scoring_version: string;
  queued_for_render: boolean;
  created_at: string;
  updated_at: string;
  generation_run_id?: string | null;
  creative_direction?: string;
  natural_boundary_confidence?: number;
}

export interface CandidateGenerationRunItem {
  id: string;
  project_id: string;
  media_asset_id: string;
  analysis_run_id: string;
  job_id?: string | null;
  creative_direction: string;
  aspect_ratio: string;
  requested_count: number;
  min_duration: number;
  max_duration: number;
  status: string;
  candidates_discovered: number;
  candidates_selected: number;
  candidates_rejected: number;
  novelty_exclusions: number;
  warnings: string[];
  error_message?: string | null;
  created_at: string;
  completed_at?: string | null;
}

export interface NoveltyHistoryItem {
  id: string;
  candidate_id: string;
  start_time: number;
  end_time: number;
  duration: number;
  creative_direction: string;
  aspect_ratio: string;
  score: number;
  title: string;
  created_at: string;
}

export interface NoveltyHistoryResponse {
  media_asset_id: string;
  total_clips_generated: number;
  total_duration_covered: number;
  history: NoveltyHistoryItem[];
}

export interface HighlightsOverview {
  project_id: string;
  total_candidates: number;
  recommended_count: number;
  needs_review_count: number;
  approved_count: number;
  rejected_count: number;
  candidates: CandidateItem[];
}

export interface DiscoverHighlightsOptions {
  analysis_run_id?: string;
  creative_direction?: string;
  aspect_ratio?: string;
  min_duration?: number;
  max_duration?: number;
  target_clip_count?: number;
  use_ai_explanations?: boolean;
  run_synchronously?: boolean;
}

export interface UpdateCandidatePayload {
  title?: string;
  description?: string;
  category?: string;
  start_time?: number;
  end_time?: number;
}

export type FramingMode = 'center' | 'manual' | 'smart_tracking';
export type AspectRatioOption = '9:16' | '1:1' | '16:9' | '4:5';

export interface CandidateClipEdit {
  id: string;
  candidate_id: string;
  project_id: string;
  media_asset_id: string;
  original_start_time: number;
  original_end_time: number;
  edited_start_time: number;
  edited_end_time: number;
  edited_duration: number;
  aspect_ratio: AspectRatioOption;
  framing_mode: FramingMode;
  manual_crop_x_pct: number;
  manual_crop_y_pct: number;
  manual_crop_zoom: number;
  tracked_subject_id?: string | null;
  tracking_status: 'none' | 'tracking' | 'tracked' | 'fallback';
  reframing_plan_id?: string | null;
  version: number;
  created_at: string;
  updated_at: string;
  media_duration?: number;
  media_width?: number;
  media_height?: number;
  candidate_title?: string;
  dominant_strategy?: string;
  detected_tracks?: Array<Record<string, unknown>>;
}

export interface CandidateClipEditSavePayload {
  edited_start_time: number;
  edited_end_time: number;
  aspect_ratio?: AspectRatioOption;
  framing_mode?: FramingMode;
  manual_crop_x_pct?: number;
  manual_crop_y_pct?: number;
  manual_crop_zoom?: number;
  tracked_subject_id?: string | null;
}

