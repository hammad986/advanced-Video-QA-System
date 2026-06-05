from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .app_constants import AppConstants


@dataclass(frozen=True)
class AppPaths:
    app_data_dir: Path
    logs_dir: Path
    config_dir: Path
    cache_dir: Path
    projects_dir: Path
    database_path: Path

    @classmethod
    def resolve(cls) -> "AppPaths":
        root = Path(
            os.environ.get(
                "ADVANCED_VIDEO_QA_PRO_HOME",
                Path(os.environ.get("LOCALAPPDATA", Path.home())) / AppConstants.ORGANIZATION_NAME,
            )
        )
        return cls(
            app_data_dir=root,
            logs_dir=root / "logs",
            config_dir=root / "config",
            cache_dir=root / "cache",
            projects_dir=root / "projects",
            database_path=root / "app.db",
        )

    def ensure(self) -> None:
        for path in (self.app_data_dir, self.logs_dir, self.config_dir, self.cache_dir, self.projects_dir):
            path.mkdir(parents=True, exist_ok=True)
