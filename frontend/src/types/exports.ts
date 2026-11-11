export type CaptionMode = 'none' | 'standard' | 'word_highlight' | 'phrase' | 'sentence';

export interface CaptionConfigItem {
  mode: CaptionMode;
  font_family: string;
  font_size: number;
  bold: boolean;
  text_color: string;
  highlight_color: string;
  outline_color: string;
  outline_width: number;
  shadow_depth: number;
  alignment: number;
  margin_v: number;
  max_words_per_line: number;
  max_lines: number;
  burn_in: boolean;
}

export interface AudioConfigItem {
  volume: number;
  fade_in_seconds: number;
  fade_out_seconds: number;
  normalize_loudness: boolean;
  sample_rate: number;
  channels: number;
}

export interface ExportPresetItem {
  preset_id: string;
  name: string;
  description: string;
  target_aspect_ratio: string;
  target_width: number;
  target_height: number;
  video_codec: string;
  audio_codec: string;
  pixel_fmt: string;
  fps: number;
  crf: number;
  video_bitrate?: string | null;
  audio_bitrate: string;
}

export interface RenderExportPayload {
  candidate_id: string;
  preset_id?: string;
  reframing_plan_id?: string;
  framing_revision_id?: string;
  title?: string;
  caption_config?: CaptionConfigItem;
  audio_config?: AudioConfigItem;
  crf?: number;
  is_preview?: boolean;
}

export interface ValidationDetailsItem {
  is_valid: boolean;
  duration: number;
  width: number;
  height: number;
  video_codec: string;
  audio_codec?: string | null;
  pixel_fmt: string;
  file_size_bytes: number;
  playable: boolean;
  errors: string[];
}

export interface ExportItem {
  id: string;
  project_id: string;
  candidate_id?: string | null;
  media_asset_id: string;
  reframing_plan_id?: string | null;
  framing_revision_id?: string | null;
  render_job_id?: string | null;
  title: string;
  export_preset: string;
  target_aspect_ratio: string;
  target_width: number;
  target_height: number;
  video_codec: string;
  audio_codec: string;
  pixel_fmt: string;
  fps: number;
  crf: number;
  video_bitrate?: string | null;
  audio_bitrate: string;
  caption_config: CaptionConfigItem;
  audio_config: AudioConfigItem;
  output_path?: string | null;
  output_filename: string;
  file_size_bytes: number;
  duration_seconds: number;
  status: 'queued' | 'rendering' | 'completed' | 'failed' | 'cancelled';
  validation_status: 'unvalidated' | 'valid' | 'invalid';
  validation_details: ValidationDetailsItem;
  error_message?: string | null;
  created_at: string;
  completed_at?: string | null;
}
