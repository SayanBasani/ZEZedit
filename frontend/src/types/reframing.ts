export interface DetectedSubjectItem {
  timestamp: number;
  box_x: number;
  box_y: number;
  box_w: number;
  box_h: number;
  confidence: number;
  category: string;
  subject_id?: string | null;
}

export interface SubjectTrackItem {
  track_id: string;
  category: string;
  first_seen: number;
  last_seen: number;
  confidence_avg: number;
  detections: DetectedSubjectItem[];
}

export interface CropKeyframeItem {
  timestamp: number;
  crop_x: number;
  crop_y: number;
  crop_w: number;
  crop_h: number;
  zoom: number;
  headroom: number;
  subject_count?: number;
  framing_strategy: string;
  is_scene_boundary?: boolean;
  is_manual_override?: boolean;
  target_center_x?: number | null;
  target_center_y?: number | null;
}

export interface ReframingRevisionItem {
  id: string;
  reframing_plan_id: string;
  revision_number: number;
  label: string;
  is_ai_generated: boolean;
  manual_overrides: Array<{
    timestamp: number;
    crop_x?: number;
    crop_y?: number;
    zoom?: number;
    headroom?: number;
    target_center_x?: number;
    target_center_y?: number;
    action?: string;
  }>;
  effective_keyframes: CropKeyframeItem[];
  render_job_id?: string | null;
  rendered_video_path?: string | null;
  rendered_duration?: number | null;
  rendered_file_size_bytes?: number | null;
  rendered_at?: string | null;
  created_at: string;
}

export interface ReframingPlanItem {
  id: string;
  project_id: string;
  media_asset_id: string;
  candidate_id?: string | null;
  job_id?: string | null;
  target_aspect_ratio: string;
  framing_strategy: string;
  status: string;
  source_width: number;
  source_height: number;
  output_width: number;
  output_height: number;
  start_time: number;
  end_time: number;
  duration: number;
  base_zoom: number;
  headroom_factor: number;
  smoothing_window_seconds: number;
  keyframes: CropKeyframeItem[];
  detected_tracks: SubjectTrackItem[];
  scene_cuts: number[];
  warnings: string[];
  active_revision_id?: string | null;
  active_revision?: ReframingRevisionItem;
  calculation_version: string;
  created_at: string;
  updated_at: string;
}

export interface CropPreviewData {
  plan_id: string;
  timestamp: number;
  crop_x: number;
  crop_y: number;
  crop_w: number;
  crop_h: number;
  zoom: number;
  strategy?: string;
  source_width: number;
  source_height: number;
  target_aspect_ratio: string;
}

export interface RenderResultPayload {
  output_path: string;
  output_width: number;
  output_height: number;
  duration: number;
  file_size_bytes: number;
  crop_w: number;
  crop_h: number;
  keyframes_count: number;
  revision_id?: string;
  revision_number?: number;
}
