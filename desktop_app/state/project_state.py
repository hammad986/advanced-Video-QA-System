from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProjectState:
    active_project_id: str | None = None
    active_project_name: str = "No Project"
    workspace_path: str | None = None
    is_dirty: bool = False

