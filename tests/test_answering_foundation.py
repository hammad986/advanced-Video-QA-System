from __future__ import annotations

import pytest

from desktop_app.answering.answer_models import INSUFFICIENT_EVIDENCE_RESPONSE
from desktop_app.answering.answer_repository import AnswerRepository
from desktop_app.answering.answer_service import AnswerService, ChatPipelineError, ProviderGeneration
from desktop_app.answering.context_builder import ContextBuilder
from desktop_app.answering.citation_builder import CitationBuilder
from desktop_app.database.database_manager import DatabaseManager
from desktop_app.evidence.evidence_models import EvidenceItem, EvidenceResult, EvidenceSource
from desktop_app.projects.project_repository import ProjectRepository
from desktop_app.projects.project_service import ProjectService
from desktop_app.widgets.chat_workspace import ChatWorkspaceWidget


class FakeEvidenceService:
    def __init__(self, items: list[EvidenceItem]) -> None:
        self.items = items

    def generate(self, *, project_id, query, embedding_selection, top_k=5, min_similarity=0.0):
        return EvidenceResult(project_id=project_id, query=query, duration_ms=10.0, items=self.items[:top_k])


class FailingEvidenceService:
    last_retrieval_count = 0

    def generate(self, *, project_id, query, embedding_selection, top_k=5, min_similarity=0.0):
        raise RuntimeError("No FAISS index found for BAAI/bge-small-en-v1.5. Build the vector index first.")


class FakeProviderExecutor:
    def __init__(self, text: str = "Unsupervised learning finds patterns without output labels [1].") -> None:
        self.text = text
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> ProviderGeneration:
        self.prompts.append(prompt)
        return ProviderGeneration(provider="fake", text=self.text)


def _evidence_item(confidence: float = 0.9) -> EvidenceItem:
    return EvidenceItem.create(
        project_id="project",
        query="What is unsupervised learning?",
        chunk_id="chunk-1",
        retrieval_rank=1,
        source=EvidenceSource(
            video_id="video-1",
            video_name="lecture.mp4",
            file_path="lecture.mp4",
            transcript_id="transcript-1",
        ),
        topic_title="Machine Learning Basics",
        start_time=1.1,
        end_time=25.1,
        similarity_score=0.91,
        confidence_score=confidence,
        chunk_text="Unsupervised learning uses inputs without output labels and finds structure in data.",
    )


def test_context_builder_requires_sufficient_evidence() -> None:
    context = ContextBuilder().build(question="What is it?", evidence_items=[_evidence_item(confidence=0.2)])

    assert context.sufficient is False
    assert context.prompt_context == ""


def test_answer_service_generates_grounded_answer_with_citations_and_history(tmp_path) -> None:
    database = DatabaseManager(tmp_path / "app.db")
    database.initialize()
    project = ProjectService(ProjectRepository(database.connection)).create_project(
        name="Answer Project",
        root_path=str(tmp_path / "project"),
    )
    repository = AnswerRepository(database.connection)
    provider = FakeProviderExecutor()
    service = AnswerService(
        repository,
        FakeEvidenceService([_evidence_item()]),
        provider,
    )

    result = service.answer(
        project_id=project.id,
        question="What is unsupervised learning?",
        embedding_selection="small",
    )
    history = repository.list_chat_history(project.id)

    assert result.provider == "fake"
    assert "[1]" in result.answer
    assert "Citations:" in result.answer
    assert result.citations[0].source_video == "lecture.mp4"
    assert provider.prompts and "Use ONLY the evidence" in provider.prompts[0]
    assert history and history[0].question == "What is unsupervised learning?"


def test_answer_service_returns_exact_insufficient_evidence_response(tmp_path) -> None:
    database = DatabaseManager(tmp_path / "app.db")
    database.initialize()
    project = ProjectService(ProjectRepository(database.connection)).create_project(
        name="Answer Project",
        root_path=str(tmp_path / "project"),
    )
    provider = FakeProviderExecutor()
    service = AnswerService(
        AnswerRepository(database.connection),
        FakeEvidenceService([_evidence_item(confidence=0.1)]),
        provider,
    )

    result = service.answer(project_id=project.id, question="Unknown topic?", embedding_selection="small")

    assert result.answer == INSUFFICIENT_EVIDENCE_RESPONSE
    assert result.provider == "none"
    assert provider.prompts == []


def test_answer_service_raises_actionable_no_faiss_error(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    database = DatabaseManager(tmp_path / "app.db")
    database.initialize()
    project = ProjectService(ProjectRepository(database.connection)).create_project(
        name="Answer Project",
        root_path=str(tmp_path / "project"),
    )
    service = AnswerService(
        AnswerRepository(database.connection),
        FailingEvidenceService(),
        FakeProviderExecutor(),
    )

    with pytest.raises(ChatPipelineError) as raised:
        service.answer(project_id=project.id, question="What is weighted sum?", embedding_selection="small")

    assert "No FAISS index available" in str(raised.value)
    log_text = (tmp_path / "logs" / "chat_pipeline.log").read_text(encoding="utf-8")
    assert '"event": "chat_failed"' in log_text
    assert "No FAISS index found" in log_text


def test_citation_builder_serializes_citations() -> None:
    citations = CitationBuilder().build([_evidence_item()])
    payload = CitationBuilder().to_json(citations)

    assert "lecture.mp4" in payload
    assert "chunk-1" in payload


def test_chat_workspace_emits_grounded_question(qapp) -> None:
    widget = ChatWorkspaceWidget()
    emitted = []
    widget.question_requested.connect(lambda question, top_k, threshold: emitted.append((question, top_k, threshold)))

    widget.question_input.setPlainText("What is unsupervised learning?")
    widget.ask_button.click()

    assert emitted == [("What is unsupervised learning?", 5, 0.0)]
