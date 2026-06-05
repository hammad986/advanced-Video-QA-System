from __future__ import annotations

from pathlib import Path

from desktop_app.projects.project_models import ResearchProject
from desktop_app.projects.project_repository import ProjectRepository


class ProjectService:
    def __init__(self, repository: ProjectRepository) -> None:
        self.repository = repository

    def create_project(
        self,
        *,
        name: str,
        description: str = "",
        root_path: str,
    ) -> ResearchProject:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Project name is required.")
        path = Path(root_path).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        return self.repository.create(
            name=clean_name,
            description=description.strip(),
            root_path=str(path),
        )

    def list_projects(self, *, include_archived: bool = False) -> list[ResearchProject]:
        return self.repository.list(include_archived=include_archived)

    def get_project(self, project_id: str) -> ResearchProject | None:
        return self.repository.get(project_id)

    def archive_project(self, project_id: str) -> ResearchProject | None:
        return self.repository.archive(project_id)

    def restore_project(self, project_id: str) -> ResearchProject | None:
        return self.repository.restore(project_id)

    def delete_project(self, project_id: str) -> bool:
        return self.repository.delete(project_id)

