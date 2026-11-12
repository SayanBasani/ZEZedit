"""Project management domain service."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from app.core.config import Settings
from app.core.errors import AppError
from app.db.connection import sqlite_session
from app.models.entities import ProjectEventRecord, ProjectRecord


class ProjectService:
    """Manages project lifecycles, configuration, and event tracking."""

    def __init__(self, settings: Settings, db_path: Path) -> None:
        self.settings = settings
        self.db_path = db_path

    def create_project(
        self,
        name: str,
        description: Optional[str] = None,
        project_config: Optional[dict] = None,
    ) -> ProjectRecord:
        """Create a new project record and record event."""
        project_id = f"proj_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        storage_subdir = project_id
        config_payload = project_config or {}

        with sqlite_session(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO projects (
                    id, name, description, status, project_config_json,
                    storage_subdir, created_at, updated_at, last_opened_at
                ) VALUES (?, ?, ?, 'active', ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    name.strip(),
                    description.strip() if description else None,
                    json.dumps(config_payload),
                    storage_subdir,
                    now,
                    now,
                    now,
                ),
            )
            # Record creation event
            self._record_event_internal(
                conn,
                project_id,
                "project_created",
                f"Project '{name.strip()}' created",
                {"name": name.strip()},
            )

        return self.get_project(project_id)

    def get_or_create_default_project(self, name: Optional[str] = None) -> ProjectRecord:
        """Get the most recently active project, or create a default project if none exists."""
        with sqlite_session(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM projects WHERE status = 'active' ORDER BY updated_at DESC LIMIT 1"
            ).fetchone()
            if row:
                return self._row_to_record(row)
        return self.create_project(
            name=name or "Default Studio Project",
            description="Main video editing workspace",
        )

    def list_projects(self, include_archived: bool = False) -> List[ProjectRecord]:
        """List active projects, optionally including archived."""
        query = "SELECT * FROM projects"
        if not include_archived:
            query += " WHERE status = 'active'"
        query += " ORDER BY updated_at DESC"

        with sqlite_session(self.db_path) as conn:
            rows = conn.execute(query).fetchall()
            return [self._row_to_record(row) for row in rows]

    def get_project(self, project_id: str) -> ProjectRecord:
        """Fetch project details by ID; updates last_opened_at."""
        now = datetime.now(timezone.utc).isoformat()
        with sqlite_session(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
            if not row:
                raise AppError(
                    code="PROJECT_NOT_FOUND",
                    message=f"Project with ID '{project_id}' does not exist.",
                    status_code=404,
                )
            conn.execute(
                "UPDATE projects SET last_opened_at = ? WHERE id = ?",
                (now, project_id),
            )
            return self._row_to_record(row)

    def update_project(
        self,
        project_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        project_config: Optional[dict] = None,
    ) -> ProjectRecord:
        """Update project metadata or configuration."""
        existing = self.get_project(project_id)
        now = datetime.now(timezone.utc).isoformat()

        new_name = name.strip() if name is not None else existing.name
        new_desc = description.strip() if description is not None else existing.description
        new_config = (
            json.dumps(project_config)
            if project_config is not None
            else json.dumps(existing.project_config)
        )

        with sqlite_session(self.db_path) as conn:
            conn.execute(
                """
                UPDATE projects
                SET name = ?, description = ?, project_config_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_name, new_desc, new_config, now, project_id),
            )
            self._record_event_internal(
                conn,
                project_id,
                "project_updated",
                f"Project '{new_name}' updated",
                {"updated_fields": [k for k, v in [("name", name), ("desc", description), ("config", project_config)] if v is not None]},
            )

        return self.get_project(project_id)

    def archive_project(self, project_id: str) -> ProjectRecord:
        """Archive a project."""
        self.get_project(project_id)
        now = datetime.now(timezone.utc).isoformat()
        with sqlite_session(self.db_path) as conn:
            conn.execute(
                "UPDATE projects SET status = 'archived', archived_at = ?, updated_at = ? WHERE id = ?",
                (now, now, project_id),
            )
            self._record_event_internal(
                conn, project_id, "project_archived", "Project archived", {}
            )
        return self.get_project(project_id)

    def restore_project(self, project_id: str) -> ProjectRecord:
        """Restore an archived project."""
        self.get_project(project_id)
        now = datetime.now(timezone.utc).isoformat()
        with sqlite_session(self.db_path) as conn:
            conn.execute(
                "UPDATE projects SET status = 'active', archived_at = NULL, updated_at = ? WHERE id = ?",
                (now, project_id),
            )
            self._record_event_internal(
                conn, project_id, "project_restored", "Project restored to active", {}
            )
        return self.get_project(project_id)

    def delete_project(self, project_id: str, confirmation: bool = False) -> None:
        """Permanently delete project metadata and child assets with explicit confirmation."""
        if not confirmation:
            raise AppError(
                code="CONFIRMATION_REQUIRED",
                message="Project deletion requires explicit confirmation parameter.",
                status_code=400,
            )
        self.get_project(project_id)
        with sqlite_session(self.db_path) as conn:
            conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))

    def get_events(self, project_id: str, limit: int = 50) -> List[ProjectEventRecord]:
        """Fetch project activity event history."""
        self.get_project(project_id)
        with sqlite_session(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM project_events WHERE project_id = ? ORDER BY created_at DESC LIMIT ?",
                (project_id, limit),
            ).fetchall()
            return [
                ProjectEventRecord(
                    id=r["id"],
                    project_id=r["project_id"],
                    event_type=r["event_type"],
                    event_summary=r["event_summary"],
                    payload=json.loads(r["payload_json"] or "{}"),
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    def _record_event_internal(
        self, conn, project_id: str, event_type: str, summary: str, payload: dict
    ) -> None:
        event_id = f"evt_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            INSERT INTO project_events (id, project_id, event_type, event_summary, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (event_id, project_id, event_type, summary, json.dumps(payload), now),
        )

    def _row_to_record(self, row) -> ProjectRecord:
        return ProjectRecord(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            status=row["status"],
            project_config=json.loads(row["project_config_json"] or "{}"),
            storage_subdir=row["storage_subdir"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_opened_at=row["last_opened_at"],
            archived_at=row["archived_at"],
        )
