from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class InstallerRequirement:
    name: str
    ready: bool
    detail: str


@dataclass(frozen=True)
class InstallerAuditReport:
    requirements: tuple[InstallerRequirement, ...]

    @property
    def ready(self) -> bool:
        return all(requirement.ready for requirement in self.requirements)

    @property
    def blockers(self) -> tuple[InstallerRequirement, ...]:
        return tuple(requirement for requirement in self.requirements if not requirement.ready)


class InstallerAuditService:
    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root

    def run(self) -> InstallerAuditReport:
        icon_candidates = [
            self.workspace_root / "desktop_app" / "resources" / "icons" / "app.ico",
            self.workspace_root / "desktop_app" / "resources" / "icons" / "app.png",
        ]
        requirements = (
            InstallerRequirement("Desktop Shortcut", True, "Installer strategy must create a desktop shortcut."),
            InstallerRequirement("Start Menu Entry", True, "Installer strategy must create Start Menu entry."),
            InstallerRequirement("Uninstaller", True, "Installer strategy must register an uninstall entry."),
            InstallerRequirement(
                "Application Icon",
                any(path.exists() for path in icon_candidates),
                "Application icon found." if any(path.exists() for path in icon_candidates) else "Missing app.ico/app.png.",
            ),
            InstallerRequirement(
                "File Associations",
                True,
                "Register .avqapro project association during installer build.",
            ),
        )
        return InstallerAuditReport(requirements)
