from __future__ import annotations

import time
import uuid
from sqlite3 import Row

from desktop_app.database.connection import DatabaseConnection
from desktop_app.projects.project_models import ProjectStatus, ResearchProject


class ProjectRepository:
    def __init__(self, connection: DatabaseConnection) -> None:
        self.connection = connection

    def create(
        self,
        *,
        name: str,
        description: str,
        root_path: str,
    ) -> ResearchProject:
        project_id = uuid.uuid4().hex
        now = time.time()
        with self.connection.connect() as connection:
            connection.execute(
                """
                INSERT INTO projects
                    (id, name, description, root_path, status, created_at, updated_at, archived_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, NULL)
                """,
                (project_id, name, description, root_path, ProjectStatus.ACTIVE.value, now, now),
            )
        return ResearchProject(
            id=project_id,
            name=name,
            description=description,
            root_path=root_path,
            status=ProjectStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

    def get(self, project_id: str) -> ResearchProject | None:
        with self.connection.connect() as connection:
            row = connection.execute(
                "SELECT * FROM projects WHERE id = ?",
                (project_id,),
            ).fetchone()
        return self._from_row(row) if row else None

    def list(self, *, include_archived: bool = False) -> list[ResearchProject]:
        sql = "SELECT * FROM projects"
        params: tuple[str, ...] = ()
        if not include_archived:
            sql += " WHERE status = ?"
            params = (ProjectStatus.ACTIVE.value,)
        sql += " ORDER BY updated_at DESC, name ASC"
        with self.connection.connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [self._from_row(row) for row in rows]

    def archive(self, project_id: str) -> ResearchProject | None:
        now = time.time()
        with self.connection.connect() as connection:
            connection.execute(
                """
                UPDATE projects
                SET status = ?, updated_at = ?, archived_at = ?
                WHERE id = ?
                """,
                (ProjectStatus.ARCHIVED.value, now, now, project_id),
            )
        return self.get(project_id)

    def restore(self, project_id: str) -> ResearchProject | None:
        now = time.time()
        with self.connection.connect() as connection:
            connection.execute(
                """
                UPDATE projects
                SET status = ?, updated_at = ?, archived_at = NULL
                WHERE id = ?
                """,
                (ProjectStatus.ACTIVE.value, now, project_id),
            )
        return self.get(project_id)

    def delete(self, project_id: str) -> bool:
        with self.connection.connect() as connection:
            cursor = connection.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            return cursor.rowcount > 0

    def _from_row(self, row: Row) -> ResearchProject:
        return ResearchProject(
            id=str(row["id"]),
            name=str(row["name"]),
            description=str(row["description"]),
            root_path=str(row["root_path"]),
            status=ProjectStatus(str(row["status"])),
            created_at=float(row["created_at"]),
            updated_at=float(row["updated_at"]),
            archived_at=float(row["archived_at"]) if row["archived_at"] is not None else None,
        )

