export interface AnalysisRunItem {
  id: string;
  media_asset_id: string;
  project_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  profile: 'fast' | 'balanced' | 'detailed';
  progress_pct: number;
  current_stage?: string;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface WordTimestamp {
  word: string;
  start: number;
  end: number;
  probability: number;
}

export interface TranscriptSegmentItem {
  id: string;
  start_time: number;
  end_time: number;
  text: string;
  language?: string;
  confidence?: number;
  words?: WordTimestamp[];
  corrected_text?: string | null;
  is_corrected?: boolean;
  correction_id?: string | null;
}

export interface SpeechTurnItem {
  id: string;
  start_time: number;
  end_time: number;
  speaker_label: string;
  text: string;
  turn_type: 'statement' | 'question' | 'exclamation' | 'pause_gap';
}

export interface TranscriptPayload {
  analysis_run_id: string;
  segments_count: number;
  turns_count: number;
  segments: TranscriptSegmentItem[];
  speech_turns: SpeechTurnItem[];
}

export interface VideoSceneItem {
  id: string;
  scene_index: number;
  start_time: number;
  end_time: number;
  representative_timestamp: number;
  thumbnail_path?: string;
  change_score: number;
}

export interface SampledFrameItem {
  id: string;
  timestamp: number;
  frame_path: string;
  scene_id?: string;
  width: number;
  height: number;
}

export interface VisualObservationItem {
  id: string;
  timestamp: number;
  frame_id?: string;
  category: 'scene_setting' | 'subjects' | 'activity' | 'on_screen_text' | 'aesthetic_note';
  description: string;
  provider_model: string;
  confidence: number;
}

export interface AudioAnalysisItem {
  id: string;
  analysis_run_id: string;
  media_asset_id: string;
  has_audio: boolean;
  sample_rate?: number | null;
  channels?: number | null;
  codec_name?: string | null;
  bit_rate?: number | null;
  duration_seconds?: number | null;
  speech_density: number;
  silence_intervals: Array<{ start: number; end: number; duration: number }>;
}

export interface TranscriptCorrectionItem {
  id: string;
  media_asset_id: string;
  segment_id?: string | null;
  start_time: number;
  end_time: number;
  original_text: string;
  corrected_text: string;
  created_at: string;
  updated_at: string;
}

export interface TemporalContextPayload {
  analysis_run_id: string;
  query_timestamp: number;
  current_scene?: VideoSceneItem | null;
  active_segment?: TranscriptSegmentItem | null;
  active_speech_turn?: SpeechTurnItem | null;
  nearby_segments: TranscriptSegmentItem[];
  nearby_visual_observations: VisualObservationItem[];
  nearest_frame?: SampledFrameItem | null;
}
