from __future__ import annotations

from desktop_app.knowledge.chunking_engine import SemanticChunkingEngine
from desktop_app.knowledge.knowledge_models import ChunkTopic, KnowledgeChunk
from desktop_app.knowledge.knowledge_repository import KnowledgeRepository
from desktop_app.knowledge.topic_extractor import TopicExtractor
from desktop_app.transcripts.transcript_repository import TranscriptRepository


class KnowledgeService:
    def __init__(
        self,
        knowledge_repository: KnowledgeRepository,
        transcript_repository: TranscriptRepository,
        *,
        chunking_engine: SemanticChunkingEngine | None = None,
        topic_extractor: TopicExtractor | None = None,
    ) -> None:
        self.knowledge_repository = knowledge_repository
        self.transcript_repository = transcript_repository
        self.chunking_engine = chunking_engine or SemanticChunkingEngine()
        self.topic_extractor = topic_extractor or TopicExtractor()

    def structure_transcript(self, transcript_id: str) -> list[KnowledgeChunk]:
        transcript = self.transcript_repository.get_transcript(transcript_id)
        if transcript is None:
            raise ValueError("Transcript was not found.")
        segments = self.transcript_repository.list_segments(transcript_id)
        drafts = self.chunking_engine.chunk(segments)
        chunks: list[KnowledgeChunk] = []
        topics: list[ChunkTopic] = []
        for draft in drafts:
            topic = self.topic_extractor.extract(draft.chunk_text)
            confidence = (draft.confidence + topic.confidence) / 2
            chunk = KnowledgeChunk.create(
                transcript_id=transcript_id,
                start_time=draft.start_time,
                end_time=draft.end_time,
                chunk_text=draft.chunk_text,
                topic_title=topic.title,
                confidence=confidence,
            )
            chunks.append(chunk)
            topics.append(ChunkTopic.create(chunk_id=chunk.chunk_id, topic_title=topic.title, confidence=topic.confidence))
        self.knowledge_repository.replace_chunks(transcript_id, chunks, topics)
        return chunks

    def list_chunks(self, transcript_id: str) -> list[KnowledgeChunk]:
        return self.knowledge_repository.list_chunks(transcript_id)

