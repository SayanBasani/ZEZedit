export type TrackType = 'video' | 'audio' | 'overlay';

export type TrackSubtype =
  | 'main_video'
  | 'secondary_video'
  | 'b_roll'
  | 'source_audio'
  | 'bgm'
  | 'voiceover'
  | 'sfx'
  | 'text'
  | 'caption'
  | 'graphics';

export type ClipType = 'video' | 'audio' | 'text' | 'overlay' | 'caption';

export type CommandType =
  | 'InsertClip'
  | 'MoveClip'
  | 'TrimClip'
  | 'SplitClip'
  | 'DeleteClip'
  | 'DuplicateClip'
  | 'AddTrack'
  | 'RemoveTrack'
  | 'UpdateTrack'
  | 'UpdateClipProps'
  | 'UpdateAudioSettings'
  | 'AddTextOverlay'
  | 'Batch';

export interface TransformProps {
  x: number;
  y: number;
  scale: number;
  rotation: number;
  crop_reference?: string | null;
}

export interface ContentProps {
  text: string;
  font_family: string;
  font_size: number;
  color: string;
  alignment: string;
  background_color?: string | null;
}

export interface AudioProps {
  fade_in: number;
  fade_out: number;
  is_muted: boolean;
}

export interface TimelineClip {
  id: string;
  timeline_id: string;
  track_id: string;
  source_media_id?: string | null;
  clip_type: ClipType;
  name: string;
  timeline_start: number;
  timeline_end: number;
  duration?: number;
  source_in: number;
  source_out: number;
  speed: number;
  volume: number;
  opacity: number;
  transform_props: TransformProps;
  content_props: ContentProps;
  audio_props: AudioProps;
  created_at: string;
  updated_at: string;
}

export interface TimelineTrack {
  id: string;
  timeline_id: string;
  name: string;
  track_type: TrackType;
  track_subtype: TrackSubtype;
  track_order: number;
  is_visible: boolean;
  is_muted: boolean;
  is_locked: boolean;
  height: number;
  created_at: string;
  updated_at: string;
  clips: TimelineClip[];
}

export interface TimelineRecord {
  id: string;
  project_id: string;
  name: string;
  duration: number;
  fps: number;
  canvas_width: number;
  canvas_height: number;
  time_base: string;
  revision: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  tracks: TimelineTrack[];
}

export interface TimelineCommandRecord {
  id: string;
  timeline_id: string;
  command_type: string;
  payload: Record<string, any>;
  inverse_payload: Record<string, any>;
  revision_before: number;
  revision_after: number;
  description: string;
  executed_by: string;
  is_undone: boolean;
  created_at: string;
}

export interface TimelineHistoryResponse {
  timeline_id: string;
  current_revision: number;
  can_undo: boolean;
  can_redo: boolean;
  history: TimelineCommandRecord[];
}

export interface AIPlanOperation {
  command_type: CommandType;
  description: string;
  parameters: Record<string, any>;
}

export interface AIEditingPlan {
  id: string;
  conversation_id: string;
  project_id: string;
  timeline_id: string;
  target_revision: number;
  user_instruction: string;
  explanation: string;
  operations: AIPlanOperation[];
  warnings: string[];
  status: 'proposed' | 'approved' | 'rejected' | 'executed' | 'failed';
  created_at: string;
  executed_at?: string | null;
}

export interface AIMessage {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  context_snapshot: Record<string, any>;
  plan?: AIEditingPlan | null;
  created_at: string;
}

export interface AIConversation {
  id: string;
  project_id: string;
  timeline_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: AIMessage[];
}

export interface CreateTimelineRequest {
  name: string;
  fps?: number;
  canvas_width?: number;
  canvas_height?: number;
  create_default_tracks?: boolean;
}

export interface InsertClipRequest {
  track_id: string;
  source_media_id?: string | null;
  clip_type?: ClipType;
  name: string;
  timeline_start: number;
  duration: number;
  source_in?: number;
  speed?: number;
  volume?: number;
}

export interface MoveClipRequest {
  clip_id: string;
  new_timeline_start: number;
  new_track_id?: string | null;
}

export interface TrimClipRequest {
  clip_id: string;
  new_timeline_start?: number | null;
  new_timeline_end?: number | null;
  new_source_in?: number | null;
  new_source_out?: number | null;
}

export interface SplitClipRequest {
  clip_id: string;
  split_time: number;
}

export interface UpdateClipPropsRequest {
  clip_id?: string;
  name?: string;
  speed?: number;
  volume?: number;
  opacity?: number;
  transform_props?: Partial<TransformProps>;
  content_props?: Partial<ContentProps>;
  audio_props?: Partial<AudioProps>;
}

export interface AddTextOverlayRequest {
  track_id?: string | null;
  text: string;
  timeline_start: number;
  duration?: number;
  font_size?: number;
  color?: string;
  alignment?: string;
  x?: number;
  y?: number;
}

export interface TimelineRenderRequest {
  preset_id?: string;
  title?: string;
  crf?: number;
  include_audio?: boolean;
}
