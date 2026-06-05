from __future__ import annotations

import time

from desktop_app.compare.compare_engine import CompareEngine
from desktop_app.compare.compare_models import CompareResult, CompareSessionRecord
from desktop_app.compare.compare_repository import CompareRepository
from desktop_app.evidence.evidence_service import EvidenceService


class CompareError(RuntimeError):
    pass


class CompareService:
    def __init__(
        self,
        compare_repository: CompareRepository,
        evidence_service: EvidenceService,
        *,
        compare_engine: CompareEngine | None = None,
    ) -> None:
        self.compare_repository = compare_repository
        self.evidence_service = evidence_service
        self.compare_engine = compare_engine or CompareEngine()

    def compare(
        self,
        *,
        project_id: str,
        session_name: str,
        video_ids: list[str],
        query: str,
        embedding_selection: str,
        min_similarity: float = 0.0,
    ) -> CompareResult:
        clean_video_ids = list(dict.fromkeys(video_ids))
        if not 2 <= len(clean_video_ids) <= 10:
            raise CompareError("Select between 2 and 10 videos to compare.")
        if not query.strip():
            raise CompareError("Comparison question is required.")
        videos = self.compare_repository.get_videos(clean_video_ids)
        if len(videos) != len(clean_video_ids):
            raise CompareError("One or more selected videos are not in the project library.")
        topics_by_video = self.compare_repository.list_topics_by_video(clean_video_ids)
        missing_knowledge = [video.name for video in videos if not topics_by_video.get(video.id)]
        if missing_knowledge:
            raise CompareError(f"Knowledge chunks are missing for: {', '.join(missing_knowledge)}.")

        started = time.perf_counter()
        evidence_result = self.evidence_service.generate(
            project_id=project_id,
            query=query,
            embedding_selection=embedding_selection,
            top_k=max(50, len(clean_video_ids) * 10),
            min_similarity=min_similarity,
        )
        selected_ids = set(clean_video_ids)
        evidence_items = [item for item in evidence_result.items if item.source.video_id in selected_ids]
        result = self.compare_engine.build_result(
            project_id=project_id,
            session_name=session_name.strip() or "Multi-Video Compare",
            query=query,
            videos=videos,
            evidence_items=evidence_items,
            topics_by_video=topics_by_video,
            duration_ms=(time.perf_counter() - started) * 1000,
            created_at=time.time(),
        )
        self.compare_repository.save_session(CompareSessionRecord.create(result=result))
        return result
