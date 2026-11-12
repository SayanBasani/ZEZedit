"""AI Video Editor Assistant Service: Context gathering, plan generation, and safe execution."""

from __future__ import annotations

import datetime
import json
import logging
import re
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import Settings, get_settings
from app.core.errors import AppError, NotFoundError, ProcessingError, ValidationError
from app.core.storage import StorageLayout
from app.db.connection import sqlite_session
from app.models.timeline import (
    AddTextOverlayRequest,
    AIConversation,
    AIEditingPlan,
    AIMessage,
    AIPlanOperation,
    ClipType,
    CommandType,
    InsertClipRequest,
    MoveClipRequest,
    SendAIMessageRequest,
    SplitClipRequest,
    TimelineClip,
    TimelineRecord,
    TrackType,
    TrimClipRequest,
    UpdateClipPropsRequest,
)
from app.services.timeline_command_service import TimelineCommandService
from app.services.timeline_service import TimelineService

logger = logging.getLogger("zezedit.timeline.ai_editor")


class AIEditorService:
    """Intelligent editing assistant producing validated, user-approved timeline editing plans."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        db_path: Optional[Path] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.layout = StorageLayout.from_root(self.settings.storage_root)
        self.db_path = db_path or self.layout.db_file
        self.timeline_service = TimelineService(self.settings, self.db_path)
        self.command_service = TimelineCommandService(self.settings, self.db_path)

    # -------------------------------------------------------------------------
    # Conversation Management
    # -------------------------------------------------------------------------

    def get_or_create_conversation(self, project_id: str, timeline_id: str) -> AIConversation:
        """Fetch or create the active AI conversation thread for a timeline."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            conv_row = conn.execute(
                "SELECT * FROM ai_conversations WHERE project_id = ? AND timeline_id = ? ORDER BY created_at DESC LIMIT 1",
                (project_id, timeline_id),
            ).fetchone()

            if conv_row:
                return self._hydrate_conversation(conn, conv_row["id"])

            conv_id = f"conv_{uuid.uuid4().hex[:12]}"
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            conn.execute(
                """
                INSERT INTO ai_conversations (id, project_id, timeline_id, title, created_at, updated_at)
                VALUES (?, ?, ?, 'AI Video Editor', ?, ?)
                """,
                (conv_id, project_id, timeline_id, now, now),
            )
            conn.commit()
            return self._hydrate_conversation(conn, conv_id)

    def send_message(
        self,
        conversation_id: str,
        request: SendAIMessageRequest,
    ) -> AIMessage:
        """Process user instruction, gather project context, generate an answer or editing plan."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            conv = conn.execute("SELECT * FROM ai_conversations WHERE id = ?", (conversation_id,)).fetchone()
            if not conv:
                raise NotFoundError(f"Conversation '{conversation_id}' not found.")

            project_id = conv["project_id"]
            timeline_id = conv["timeline_id"]

            # Save user message
            user_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            context_snap = {
                "playhead_time": request.playhead_time,
                "selected_clip_id": request.selected_clip_id,
                "selected_track_id": request.selected_track_id,
            }

            conn.execute(
                """
                INSERT INTO ai_messages (id, conversation_id, role, content, context_snapshot, plan_id, created_at)
                VALUES (?, ?, 'user', ?, ?, NULL, ?)
                """,
                (user_msg_id, conversation_id, request.message, json.dumps(context_snap), now),
            )
            conn.commit()

        # Gather relevant project context
        context = self._gather_project_context(
            project_id=project_id,
            timeline_id=timeline_id,
            playhead_time=request.playhead_time,
            selected_clip_id=request.selected_clip_id,
        )

        # Generate answer or structured editing plan
        reply_text, proposed_plan = self._reason_and_plan(
            conversation_id=conversation_id,
            project_id=project_id,
            timeline_id=timeline_id,
            user_text=request.message,
            context=context,
        )

        plan_id = None
        if proposed_plan:
            plan_id = proposed_plan.id
            # Persist plan
            with sqlite_session(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO ai_editing_plans (
                        id, conversation_id, project_id, timeline_id, target_revision,
                        user_instruction, explanation, operations, warnings, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'proposed', ?)
                    """,
                    (
                        proposed_plan.id,
                        conversation_id,
                        project_id,
                        timeline_id,
                        proposed_plan.target_revision,
                        proposed_plan.user_instruction,
                        proposed_plan.explanation,
                        json.dumps([op.model_dump() for op in proposed_plan.operations]),
                        json.dumps(proposed_plan.warnings),
                        proposed_plan.created_at,
                    ),
                )
                conn.commit()

        # Save assistant message
        asst_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with sqlite_session(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO ai_messages (id, conversation_id, role, content, context_snapshot, plan_id, created_at)
                VALUES (?, ?, 'assistant', ?, '{}', ?, ?)
                """,
                (asst_msg_id, conversation_id, reply_text, plan_id, now),
            )
            conn.commit()

        return AIMessage(
            id=asst_msg_id,
            conversation_id=conversation_id,
            role="assistant",
            content=reply_text,
            context_snapshot={},
            plan=proposed_plan,
            created_at=now,
        )

    # -------------------------------------------------------------------------
    # Plan Approval & Safe Execution
    # -------------------------------------------------------------------------

    def get_plan(self, plan_id: str) -> AIEditingPlan:
        """Fetch plan details."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM ai_editing_plans WHERE id = ?", (plan_id,)).fetchone()
            if not row:
                raise NotFoundError(f"Plan '{plan_id}' not found.")
            return self._row_to_plan(row)

    def approve_and_execute_plan(self, plan_id: str) -> TimelineRecord:
        """Execute all operations in an approved editing plan through TimelineCommandService."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM ai_editing_plans WHERE id = ?", (plan_id,)).fetchone()
            if not row:
                raise NotFoundError(f"Plan '{plan_id}' not found.")

            if row["status"] == "executed":
                raise ValidationError("Plan has already been executed.")

            timeline_id = row["timeline_id"]
            tl = conn.execute("SELECT revision FROM timelines WHERE id = ?", (timeline_id,)).fetchone()
            current_rev = int(tl["revision"])
            target_rev = int(row["target_revision"])

            # Verify revision matches or warn
            if current_rev != target_rev:
                logger.warning(
                    "Executing plan %s on timeline revision %d (planned on %d)",
                    plan_id, current_rev, target_rev
                )

            operations = json.loads(row["operations"])

        # Execute operations via command service
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            for op in operations:
                cmd_type = op["command_type"]
                params = op["parameters"]

                if cmd_type == CommandType.INSERT_CLIP.value:
                    self.command_service.insert_clip(
                        timeline_id=timeline_id,
                        request=InsertClipRequest(**params),
                        executed_by="ai",
                    )
                elif cmd_type == CommandType.MOVE_CLIP.value:
                    self.command_service.move_clip(
                        timeline_id=timeline_id,
                        request=MoveClipRequest(**params),
                        executed_by="ai",
                    )
                elif cmd_type == CommandType.TRIM_CLIP.value:
                    self.command_service.trim_clip(
                        timeline_id=timeline_id,
                        request=TrimClipRequest(**params),
                        executed_by="ai",
                    )
                elif cmd_type == CommandType.SPLIT_CLIP.value:
                    self.command_service.split_clip(
                        timeline_id=timeline_id,
                        request=SplitClipRequest(**params),
                        executed_by="ai",
                    )
                elif cmd_type == CommandType.DELETE_CLIP.value:
                    self.command_service.delete_clip(
                        timeline_id=timeline_id,
                        clip_id=params["clip_id"],
                        executed_by="ai",
                    )
                elif cmd_type == CommandType.UPDATE_CLIP_PROPS.value:
                    self.command_service.update_clip_props(
                        timeline_id=timeline_id,
                        request=UpdateClipPropsRequest(**params),
                        executed_by="ai",
                    )
                elif cmd_type == CommandType.ADD_TEXT_OVERLAY.value:
                    self.command_service.add_text_overlay(
                        timeline_id=timeline_id,
                        request=AddTextOverlayRequest(**params),
                        executed_by="ai",
                    )

            with sqlite_session(self.db_path) as conn:
                conn.execute(
                    "UPDATE ai_editing_plans SET status = 'executed', executed_at = ? WHERE id = ?",
                    (now, plan_id),
                )
                conn.commit()

            return self.timeline_service.get_timeline(timeline_id)

        except Exception as exc:
            with sqlite_session(self.db_path) as conn:
                conn.execute("UPDATE ai_editing_plans SET status = 'failed' WHERE id = ?", (plan_id,))
                conn.commit()
            logger.error("Failed to execute AI editing plan %s: %s", plan_id, exc)
            raise ProcessingError(f"Plan execution failed: {exc}")

    def reject_plan(self, plan_id: str) -> AIEditingPlan:
        """Mark an AI editing plan as rejected by user."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("UPDATE ai_editing_plans SET status = 'rejected' WHERE id = ?", (plan_id,))
            conn.commit()
            return self.get_plan(plan_id)

    def list_plans(self, timeline_id: str) -> List[AIEditingPlan]:
        """List all AI editing plans / versions for a timeline ordered by creation date."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM ai_editing_plans WHERE timeline_id = ? ORDER BY created_at DESC",
                (timeline_id,),
            ).fetchall()
            return [self._row_to_plan(r) for r in rows]

    def restore_plan(self, plan_id: str) -> TimelineRecord:
        """Restore a previous AI editing plan.
        If the plan was not yet executed (or was rejected), executes the plan operations.
        If the plan was already executed, rolls back any newer commands executed after it
        to return the timeline to this plan's exact state.
        """
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM ai_editing_plans WHERE id = ?", (plan_id,)).fetchone()
            if not row:
                raise NotFoundError(f"Plan '{plan_id}' not found.")

            timeline_id = row["timeline_id"]
            plan_status = row["status"]
            executed_at = row["executed_at"]

        if plan_status != "executed":
            return self.approve_and_execute_plan(plan_id)

        # Plan was already executed; roll back commands that occurred after this plan
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            newer_commands = conn.execute(
                "SELECT * FROM timeline_commands WHERE timeline_id = ? AND created_at > ? AND is_undone = 0 ORDER BY revision_after DESC",
                (timeline_id, executed_at or row["created_at"]),
            ).fetchall()

        for cmd in newer_commands:
            try:
                self.command_service.undo(timeline_id)
            except Exception as e:
                logger.warning("Could not undo command %s during plan restore: %s", cmd["id"], e)

        return self.timeline_service.get_timeline(timeline_id)

    # -------------------------------------------------------------------------
    # Context Aggregator & Semantic Rule Engine
    # -------------------------------------------------------------------------

    def _gather_project_context(
        self,
        project_id: str,
        timeline_id: str,
        playhead_time: Optional[float] = None,
        selected_clip_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Aggregate media, transcripts, highlights, and timeline state."""
        with sqlite_session(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            proj = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
            media_rows = conn.execute(
                "SELECT id, original_filename as filename, duration_seconds, width, height FROM media_assets WHERE project_id = ?",
                (project_id,),
            ).fetchall()
            cand_rows = conn.execute(
                "SELECT id, title, start_time, end_time, quality_score as score, category as virality_label FROM shorts_candidates WHERE project_id = ? ORDER BY quality_score DESC LIMIT 5",
                (project_id,),
            ).fetchall()
            trans_rows = conn.execute(
                """
                SELECT ts.start_time, ts.end_time, ts.text as clean_text
                FROM transcript_segments ts
                JOIN media_assets ma ON ma.id = ts.media_asset_id
                WHERE ma.project_id = ?
                ORDER BY ts.start_time ASC LIMIT 30
                """,
                (project_id,),
            ).fetchall()

        timeline = self.timeline_service.get_timeline(timeline_id)

        # Locate selected clip if any
        selected_clip = None
        if selected_clip_id:
            for tr in timeline.tracks:
                for cl in tr.clips:
                    if cl.id == selected_clip_id:
                        selected_clip = cl
                        break

        return {
            "project_name": proj["name"] if proj else "Project",
            "media_assets": [dict(r) for r in media_rows],
            "candidates": [dict(r) for r in cand_rows],
            "transcripts": [dict(r) for r in trans_rows],
            "timeline": timeline,
            "playhead_time": playhead_time or 0.0,
            "selected_clip": selected_clip,
        }

    def _reason_and_plan(
        self,
        conversation_id: str,
        project_id: str,
        timeline_id: str,
        user_text: str,
        context: Dict[str, Any],
    ) -> Tuple[str, Optional[AIEditingPlan]]:
        """Interpret user request and either answer questions or return a structured plan."""
        text_lower = user_text.lower().strip()
        tl: TimelineRecord = context["timeline"]
        playhead = float(context["playhead_time"])
        selected_clip: Optional[TimelineClip] = context["selected_clip"]
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        plan_id = f"plan_{uuid.uuid4().hex[:12]}"

        # 1. Informational Queries: "what is happening around X", "who is speaking", "find highlights"
        if "?" in user_text or text_lower.startswith(("what", "who", "where", "how", "tell me", "summarize", "find")):
            # Look up transcript around requested time or playhead
            time_match = re.search(r"(\d+)\s*(?:min|m|minute|sec|s|second)", text_lower)
            query_time = playhead
            if time_match:
                val = float(time_match.group(1))
                if "min" in time_match.group(0):
                    query_time = val * 60.0
                else:
                    query_time = val

            matching_dialogue = [
                t for t in context["transcripts"]
                if float(t["start_time"]) <= query_time + 15.0 and float(t["end_time"]) >= max(0, query_time - 15.0)
            ]

            if matching_dialogue:
                dialogue_snippet = " ".join(t["clean_text"] for t in matching_dialogue[:3])
                return (
                    f"Around {query_time:.1f}s, the transcript records: \"{dialogue_snippet}\"",
                    None,
                )

            if context["candidates"]:
                top = context["candidates"][0]
                return (
                    f"I found {len(context['candidates'])} highlight candidate(s) in this project. "
                    f"Top candidate '{top['title']}' ({top['start_time']}s - {top['end_time']}s) "
                    f"has a virality score of {float(top['score']) * 100:.0f}%.",
                    None,
                )

            return (
                f"Project '{context['project_name']}' has {len(context['media_assets'])} media asset(s) and "
                f"{len(tl.tracks)} tracks with duration {tl.duration:.1f}s. Ask me to trim clips, add overlays, or split sections!",
                None,
            )

        # 2. Plan Generation: "split clip at playhead" or "split"
        if "split" in text_lower:
            target_clip = selected_clip
            if not target_clip:
                # Find clip under playhead
                for tr in tl.tracks:
                    for cl in tr.clips:
                        if cl.timeline_start <= playhead <= cl.timeline_end:
                            target_clip = cl
                            break
                    if target_clip:
                        break

            if not target_clip:
                return ("Please select a clip or position the playhead over a clip to split.", None)

            split_pos = playhead if target_clip.timeline_start < playhead < target_clip.timeline_end else (target_clip.timeline_start + target_clip.duration / 2.0)
            split_pos = round(split_pos, 2)

            ops = [
                AIPlanOperation(
                    command_type=CommandType.SPLIT_CLIP,
                    description=f"Split clip '{target_clip.name}' at {split_pos:.2f}s",
                    parameters={"clip_id": target_clip.id, "split_time": split_pos},
                )
            ]
            plan = AIEditingPlan(
                id=plan_id,
                conversation_id=conversation_id,
                project_id=project_id,
                timeline_id=timeline_id,
                target_revision=tl.revision,
                user_instruction=user_text,
                explanation=f"Splits clip '{target_clip.name}' into two separate segments at {split_pos:.2f}s.",
                operations=ops,
                warnings=[],
                status="proposed",
                created_at=now,
            )
            return ("I generated a plan to split the clip. Please review and approve:", plan)

        # 3. Plan Generation: "add text / overlay"
        if "text" in text_lower or "title" in text_lower or "caption" in text_lower or "overlay" in text_lower:
            text_content = "Highlight Moment"
            quote_match = re.search(r"['\"]([^'\"]+)['\"]", user_text)
            if quote_match:
                text_content = quote_match.group(1)

            start_t = playhead
            ops = [
                AIPlanOperation(
                    command_type=CommandType.ADD_TEXT_OVERLAY,
                    description=f"Add text overlay '{text_content}' at {start_t:.2f}s",
                    parameters={
                        "text": text_content,
                        "timeline_start": round(start_t, 2),
                        "duration": 4.0,
                        "font_size": 52,
                        "color": "#FFCC00",
                        "alignment": "center",
                    },
                )
            ]
            plan = AIEditingPlan(
                id=plan_id,
                conversation_id=conversation_id,
                project_id=project_id,
                timeline_id=timeline_id,
                target_revision=tl.revision,
                user_instruction=user_text,
                explanation=f"Inserts high-visibility text overlay '{text_content}' on the overlay track.",
                operations=ops,
                warnings=[],
                status="proposed",
                created_at=now,
            )
            return ("Here is the proposed text overlay plan:", plan)

        # 4. Plan Generation: "mute" or "volume"
        if "volume" in text_lower or "quieter" in text_lower or "louder" in text_lower or "mute" in text_lower:
            target_clip = selected_clip
            if not target_clip:
                for tr in tl.tracks:
                    if tr.clips:
                        target_clip = tr.clips[0]
                        break

            if not target_clip:
                return ("No clip found to adjust audio volume.", None)

            target_vol = 0.5
            if "mute" in text_lower:
                target_vol = 0.0
            elif "louder" in text_lower:
                target_vol = 1.5

            ops = [
                AIPlanOperation(
                    command_type=CommandType.UPDATE_CLIP_PROPS,
                    description=f"Set volume of '{target_clip.name}' to {int(target_vol * 100)}%",
                    parameters={"clip_id": target_clip.id, "volume": target_vol},
                )
            ]
            plan = AIEditingPlan(
                id=plan_id,
                conversation_id=conversation_id,
                project_id=project_id,
                timeline_id=timeline_id,
                target_revision=tl.revision,
                user_instruction=user_text,
                explanation=f"Adjusts audio level of '{target_clip.name}' to {target_vol:.1f}x.",
                operations=ops,
                warnings=[],
                status="proposed",
                created_at=now,
            )
            return ("I generated an audio adjustment plan:", plan)

        # 5. Plan Generation: "trim" or "shorten"
        if "trim" in text_lower or "shorten" in text_lower:
            target_clip = selected_clip
            if not target_clip:
                for tr in tl.tracks:
                    if tr.clips:
                        target_clip = tr.clips[-1]
                        break

            if not target_clip:
                return ("No clip available to trim.", None)

            cur_dur = target_clip.duration
            new_dur = max(1.0, round(cur_dur * 0.75, 2))
            new_end = round(target_clip.timeline_start + new_dur, 2)

            ops = [
                AIPlanOperation(
                    command_type=CommandType.TRIM_CLIP,
                    description=f"Trim '{target_clip.name}' end to {new_end:.2f}s (duration {new_dur:.2f}s)",
                    parameters={"clip_id": target_clip.id, "new_timeline_end": new_end},
                )
            ]
            plan = AIEditingPlan(
                id=plan_id,
                conversation_id=conversation_id,
                project_id=project_id,
                timeline_id=timeline_id,
                target_revision=tl.revision,
                user_instruction=user_text,
                explanation=f"Shortens '{target_clip.name}' by 25% to tighten pacing.",
                operations=ops,
                warnings=["This will reduce the clip's duration on the timeline."],
                status="proposed",
                created_at=now,
            )
            return ("Here is the proposed trim plan:", plan)

        # 6. Plan Generation: "delete" or "remove"
        if "delete" in text_lower or "remove" in text_lower:
            target_clip = selected_clip
            if not target_clip:
                return ("Please select the clip you want to delete.", None)

            ops = [
                AIPlanOperation(
                    command_type=CommandType.DELETE_CLIP,
                    description=f"Delete clip '{target_clip.name}'",
                    parameters={"clip_id": target_clip.id},
                )
            ]
            plan = AIEditingPlan(
                id=plan_id,
                conversation_id=conversation_id,
                project_id=project_id,
                timeline_id=timeline_id,
                target_revision=tl.revision,
                user_instruction=user_text,
                explanation=f"Removes clip '{target_clip.name}' from track.",
                operations=ops,
                warnings=["Destructive operation: this clip will be deleted (reversible via Undo)."],
                status="proposed",
                created_at=now,
            )
            return ("I generated a clip deletion plan with a safety warning:", plan)

        # 7. Fallback: Populate timeline from top highlight candidate if empty
        if ("create" in text_lower or "populate" in text_lower or "short" in text_lower) and context["candidates"]:
            cand = context["candidates"][0]
            cand_dur = round(float(cand["end_time"]) - float(cand["start_time"]), 2)
            # Find main video track
            v_track = next((t for t in tl.tracks if t.track_type == TrackType.VIDEO), tl.tracks[0])

            # Resolve media
            source_media_id = context["media_assets"][0]["id"] if context["media_assets"] else None

            ops = [
                AIPlanOperation(
                    command_type=CommandType.INSERT_CLIP,
                    description=f"Insert top highlight '{cand['title']}' ({cand_dur:.1f}s)",
                    parameters={
                        "track_id": v_track.id,
                        "source_media_id": source_media_id,
                        "clip_type": ClipType.VIDEO.value,
                        "name": cand["title"],
                        "timeline_start": 0.0,
                        "duration": cand_dur,
                        "source_in": float(cand["start_time"]),
                    },
                )
            ]
            plan = AIEditingPlan(
                id=plan_id,
                conversation_id=conversation_id,
                project_id=project_id,
                timeline_id=timeline_id,
                target_revision=tl.revision,
                user_instruction=user_text,
                explanation=f"Populates timeline with top AI highlight '{cand['title']}'.",
                operations=ops,
                warnings=[],
                status="proposed",
                created_at=now,
            )
            return ("I created a plan to insert your top highlight candidate into the timeline:", plan)

        return (
            f"I can help you edit this timeline. Try asking: "
            f"'Split clip at playhead', 'Add text overlay \"Watch This!\"', 'Shorten this clip', or 'Mute music track'.",
            None,
        )

    # -------------------------------------------------------------------------
    # Private Helpers
    # -------------------------------------------------------------------------

    def _hydrate_conversation(self, conn: sqlite3.Connection, conv_id: str) -> AIConversation:
        conv_row = conn.execute("SELECT * FROM ai_conversations WHERE id = ?", (conv_id,)).fetchone()
        if not conv_row:
            raise NotFoundError(f"Conversation '{conv_id}' not found.")

        msg_rows = conn.execute(
            "SELECT * FROM ai_messages WHERE conversation_id = ? ORDER BY created_at ASC",
            (conv_id,),
        ).fetchall()

        messages = []
        for mr in msg_rows:
            plan = None
            if mr["plan_id"]:
                plan_row = conn.execute("SELECT * FROM ai_editing_plans WHERE id = ?", (mr["plan_id"],)).fetchone()
                if plan_row:
                    plan = self._row_to_plan(plan_row)

            messages.append(
                AIMessage(
                    id=mr["id"],
                    conversation_id=mr["conversation_id"],
                    role=mr["role"],
                    content=mr["content"],
                    context_snapshot=json.loads(mr["context_snapshot"] or "{}"),
                    plan=plan,
                    created_at=mr["created_at"],
                )
            )

        return AIConversation(
            id=conv_row["id"],
            project_id=conv_row["project_id"],
            timeline_id=conv_row["timeline_id"],
            title=conv_row["title"],
            created_at=conv_row["created_at"],
            updated_at=conv_row["updated_at"],
            messages=messages,
        )

    def _row_to_plan(self, row: sqlite3.Row) -> AIEditingPlan:
        ops_data = json.loads(row["operations"] or "[]")
        operations = [
            AIPlanOperation(
                command_type=CommandType(op["command_type"]),
                description=op["description"],
                parameters=op["parameters"],
            )
            for op in ops_data
        ]
        return AIEditingPlan(
            id=row["id"],
            conversation_id=row["conversation_id"],
            project_id=row["project_id"],
            timeline_id=row["timeline_id"],
            target_revision=int(row["target_revision"]),
            user_instruction=row["user_instruction"],
            explanation=row["explanation"],
            operations=operations,
            warnings=json.loads(row["warnings"] or "[]"),
            status=row["status"],
            created_at=row["created_at"],
            executed_at=row["executed_at"],
        )
