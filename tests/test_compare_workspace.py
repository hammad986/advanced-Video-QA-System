from __future__ import annotations

import time

from desktop_app.compare.compare_repository import CompareRepository
from desktop_app.compare.compare_service import CompareService
from desktop_app.database.database_manager import DatabaseManager
from desktop_app.evidence.evidence_models import EvidenceItem, EvidenceResult, EvidenceSource
from desktop_app.projects.project_repository import ProjectRepository
from desktop_app.projects.project_service import ProjectService
from desktop_app.widgets.compare_workspace import CompareWorkspaceWidget


class FakeEvidenceService:
    def __init__(self, items: list[EvidenceItem]) -> None:
        self.items = items
        self.calls: list[dict[str, object]] = []

    def generate(self, *, project_id, query, embedding_selection, top_k=5, min_similarity=0.0):
        self.calls.append(
            {
                "project_id": project_id,
                "query": query,
                "embedding_selection": embedding_selection,
                "top_k": top_k,
                "min_similarity": min_similarity,
            }
        )
        return EvidenceResult(project_id=project_id, query=query, duration_ms=5.0, items=self.items[:top_k])


def test_compare_service_detects_findings_and_persists_session(tmp_path) -> None:
    database = DatabaseManager(tmp_path / "app.db")
    database.initialize()
    project = ProjectService(ProjectRepository(database.connection)).create_project(
        name="Compare Project",
        root_path=str(tmp_path / "project"),
    )
    video_a, video_b = _seed_compare_data(database, project.id)
    evidence = [
        _evidence(project.id, video_a, "chunk-a-1", "Machine Learning Basics", "Learning patterns from data."),
        _evidence(project.id, video_b, "chunk-b-1", "Machine Learning Basics", "Learning patterns with examples."),
        _evidence(project.id, video_b, "chunk-b-2", "Neural Networks", "Neural networks are covered in this video."),
    ]
    fake_evidence = FakeEvidenceService(evidence)
    repository = CompareRepository(database.connection)
    service = CompareService(repository, fake_evidence)

    result = service.compare(
        project_id=project.id,
        session_name="Compare ML",
        video_ids=[video_a["id"], video_b["id"]],
        query="Compare machine learning definitions",
        embedding_selection="small",
    )
    sessions = repository.list_sessions(project.id)

    assert fake_evidence.calls[0]["top_k"] == 50
    assert result.agreements
    assert result.unique_concepts
    assert result.differences
    assert len(result.evidence_items) == 3
    assert sessions and sessions[0].query == "Compare machine learning definitions"
    assert "agreements" in sessions[0].result_json


def test_compare_service_requires_two_to_ten_videos(tmp_path) -> None:
    database = DatabaseManager(tmp_path / "app.db")
    database.initialize()
    project = ProjectService(ProjectRepository(database.connection)).create_project(
        name="Compare Project",
        root_path=str(tmp_path / "project"),
    )
    video_a, _ = _seed_compare_data(database, project.id)
    service = CompareService(CompareRepository(database.connection), FakeEvidenceService([]))

    try:
        service.compare(
            project_id=project.id,
            session_name="Invalid",
            video_ids=[video_a["id"]],
            query="Compare",
            embedding_selection="small",
        )
    except Exception as exc:
        assert "between 2 and 10" in str(exc)
    else:
        raise AssertionError("Expected compare to reject a single video")


def test_compare_workspace_emits_selected_videos(qapp) -> None:
    widget = CompareWorkspaceWidget()
    videos = [_video_record_dict("video-a", "a.mp4"), _video_record_dict("video-b", "b.mp4")]
    widget.set_videos([_video_object(video) for video in videos])
    for row in range(widget.video_list.count()):
        widget.video_list.item(row).setSelected(True)
    emitted = []
    widget.compare_requested.connect(lambda session, ids, query, threshold: emitted.append((session, ids, query, threshold)))

    widget.session_name_input.setText("Compare Session")
    widget.query_input.setText("What differs?")
    widget.compare_button.click()

    assert emitted == [("Compare Session", ["video-a", "video-b"], "What differs?", 0.0)]


def _seed_compare_data(database: DatabaseManager, project_id: str) -> tuple[dict[str, object], dict[str, object]]:
    video_a = _video_record_dict("video-a", "01_index.mp4")
    video_b = _video_record_dict("video-b", "02_index.mp4")
    now = time.time()
    with database.connection.connect() as connection:
        for video in (video_a, video_b):
            connection.execute(
                """
                INSERT INTO videos (
                    id, project_id, name, file_path, file_size, duration, fps,
                    width, height, thumbnail_path, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    video["id"],
                    project_id,
                    video["name"],
                    video["file_path"],
                    100,
                    60.0,
                    30.0,
                    1280,
                    720,
                    "",
                    now,
                    now,
                ),
            )
        for transcript_id, video_id in (("transcript-a", "video-a"), ("transcript-b", "video-b")):
            connection.execute(
                "INSERT INTO transcripts (id, video_id, language, model_name, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (transcript_id, video_id, "en", "base", "completed", now),
            )
        chunks = (
            ("chunk-a-1", "transcript-a", 1.0, 10.0, "Machine learning learns patterns from data.", "Machine Learning Basics"),
            ("chunk-b-1", "transcript-b", 2.0, 12.0, "Machine learning learns patterns with examples.", "Machine Learning Basics"),
            ("chunk-b-2", "transcript-b", 20.0, 30.0, "Neural networks are model structures.", "Neural Networks"),
        )
        for chunk in chunks:
            connection.execute(
                """
                INSERT INTO knowledge_chunks (
                    chunk_id, transcript_id, start_time, end_time, chunk_text,
                    topic_title, confidence, word_count, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (*chunk, 0.9, 8, now),
            )
    return video_a, video_b


def _video_record_dict(video_id: str, name: str) -> dict[str, object]:
    return {"id": video_id, "name": name, "file_path": f"D:/videos/{name}"}


def _video_object(video: dict[str, object]):
    from desktop_app.videos.video_model import VideoRecord

    now = time.time()
    return VideoRecord(
        id=str(video["id"]),
        project_id="project",
        name=str(video["name"]),
        file_path=str(video["file_path"]),
        file_size=100,
        duration=60.0,
        fps=30.0,
        width=1280,
        height=720,
        thumbnail_path="",
        created_at=now,
        updated_at=now,
    )


def _evidence(
    project_id: str,
    video: dict[str, object],
    chunk_id: str,
    topic: str,
    text: str,
) -> EvidenceItem:
    return EvidenceItem.create(
        project_id=project_id,
        query="Compare machine learning definitions",
        chunk_id=chunk_id,
        retrieval_rank=1,
        source=EvidenceSource(
            video_id=str(video["id"]),
            video_name=str(video["name"]),
            file_path=str(video["file_path"]),
            transcript_id=f"transcript-{str(video['id']).split('-')[-1]}",
        ),
        topic_title=topic,
        start_time=1.0,
        end_time=10.0,
        similarity_score=0.9,
        confidence_score=0.86,
        chunk_text=text,
    )
