/**
 * TypeScript definitions for Milestone 10: Character Extraction Studio & Character Library
 */

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface CharacterObservation {
  id: string;
  candidate_id: string;
  job_id: string;
  project_id: string;
  media_asset_id: string;
  timestamp: number;
  frame_path?: string;
  thumbnail_path: string;
  bounding_box: BoundingBox;
  detection_type: string;
  confidence: number;
  detection_method: string;
  unverified_dialogue?: string | null;
  is_detached: boolean;
  created_at: string;
}

export type ReviewStatus = 'provisional' | 'confirmed' | 'rejected' | 'merged' | 'split';

export interface CharacterCandidate {
  id: string;
  job_id: string;
  project_id: string;
  label: string;
  review_status: ReviewStatus;
  confirmed_character_id?: string | null;
  observation_count: number;
  sampled_screen_time_seconds: number;
  estimated_screen_time_seconds: number;
  representative_thumbnail_path?: string | null;
  detection_methodology: string;
  clustering_confidence: number;
  notes: string;
  observations: CharacterObservation[];
  created_at: string;
  updated_at: string;
}

export interface CharacterProfile {
  id: string;
  project_id: string;
  name: string;
  avatar_path?: string | null;
  biography: string;
  appearance_tags: string[];
  total_appearances: number;
  total_screen_time_seconds: number;
  metadata_json: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface ExtractionJobConfig {
  media_asset_id: string;
  sample_interval_sec: number;
  detector_model?: string;
  min_face_size?: number;
  detect_persons?: boolean;
}

export interface ExtractionJobStatus {
  id: string;
  job_id?: string | null;
  project_id: string;
  media_asset_id: string;
  status: string;
  sample_interval_sec: number;
  detector_model: string;
  frames_sampled: number;
  detections_count: number;
  candidates_count: number;
  duration_seconds: number;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface RenameCandidateRequest {
  label: string;
}

export interface ConfirmCandidateRequest {
  name?: string;
  biography?: string;
  appearance_tags?: string[];
  existing_character_id?: string;
}

export interface MergeCandidatesRequest {
  source_candidate_ids: string[];
  target_candidate_id: string;
  new_label?: string;
}

export interface SplitCandidateRequest {
  candidate_id?: string;
  observation_ids_to_split: string[];
  new_candidate_label: string;
}

export interface UpdateProfileRequest {
  name?: string;
  biography?: string;
  appearance_tags?: string[];
}

export interface CharacterExportPayload {
  export_version: string;
  exported_at: string;
  profile: CharacterProfile;
  associated_candidates: any[];
  screen_time_summary: {
    total_appearances: number;
    total_screen_time_seconds: number;
    candidate_clusters_count: number;
  };
  disclaimer: string;
}
