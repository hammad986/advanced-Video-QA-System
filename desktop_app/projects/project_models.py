from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


@dataclass(frozen=True)
class ResearchProject:
    id: str
    name: str
    description: str
    root_path: str
    status: ProjectStatus
    created_at: float
    updated_at: float
    archived_at: float | None = None

