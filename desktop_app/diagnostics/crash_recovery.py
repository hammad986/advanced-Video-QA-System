from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RecoverySnapshot:
    project_id: str
    project_name: str
    workspace_path: str
    chat_session_id: str
    compare_session_id: str
    video_path: str
    video_position_ms: int
    layout: dict[str, int]
    captured_at: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "workspace_path": self.workspace_path,
            "chat_session_id": self.chat_session_id,
            "compare_session_id": self.compare_session_id,
            "video_path": self.video_path,
            "video_position_ms": self.video_position_ms,
            "layout": self.layout,
            "captured_at": self.captured_at,
        }


class SessionRecoveryService:
    def __init__(self, recovery_path: Path) -> None:
        self.recovery_path = recovery_path

    def save_snapshot(self, snapshot: RecoverySnapshot) -> Path:
        self.recovery_path.parent.mkdir(parents=True, exist_ok=True)
        self.recovery_path.write_text(json.dumps(snapshot.to_dict(), indent=2), encoding="utf-8")
        return self.recovery_path

    def load_snapshot(self) -> dict[str, Any] | None:
        if not self.recovery_path.exists():
            return None
        try:
            payload = json.loads(self.recovery_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None

    def clear_snapshot(self) -> None:
        if self.recovery_path.exists():
            self.recovery_path.unlink()

    @staticmethod
    def create_snapshot(
        *,
        project_id: str = "",
        project_name: str = "",
        workspace_path: str = "",
        chat_session_id: str = "",
        compare_session_id: str = "",
        video_path: str = "",
        video_position_ms: int = 0,
        layout: dict[str, int] | None = None,
    ) -> RecoverySnapshot:
        return RecoverySnapshot(
            project_id=project_id,
            project_name=project_name,
            workspace_path=workspace_path,
            chat_session_id=chat_session_id,
            compare_session_id=compare_session_id,
            video_path=video_path,
            video_position_ms=max(0, video_position_ms),
            layout=layout or {},
            captured_at=time.time(),
        )
