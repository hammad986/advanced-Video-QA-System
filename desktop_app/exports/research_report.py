from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field

from desktop_app.bookmarks.bookmark_models import Bookmark
from desktop_app.chat.chat_models import ChatMessage, ChatSession
from desktop_app.compare.compare_models import CompareSessionRecord
from desktop_app.evidence.evidence_models import EvidenceHistoryRecord
from desktop_app.highlights.highlight_models import Highlight


@dataclass(frozen=True)
class ResearchReport:
    title: str
    summary: str
    key_findings: list[str]
    evidence: list[dict[str, object]]
    contradictions: list[str]
    open_questions: list[str]
    references: list[str]
    created_at: float = field(default_factory=time.time)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    def to_markdown(self) -> str:
        lines = [
            f"# {self.title}",
            "",
            "## Summary",
            self.summary or "No summary available.",
            "",
            "## Key Findings",
            *[f"- {finding}" for finding in self.key_findings or ["No key findings recorded."]],
            "",
            "## Evidence",
        ]
        for item in self.evidence:
            lines.append(
                f"- Rank {item.get('rank', '?')}: {item.get('query', '')} "
                f"(chunk `{item.get('chunk_id', '')}`, confidence {float(item.get('confidence_score', 0.0)):.2f})"
            )
        lines.extend(
            [
                "",
                "## Contradictions",
                *[f"- {item}" for item in self.contradictions or ["None identified."]],
                "",
                "## Open Questions",
                *[f"- {item}" for item in self.open_questions or ["None recorded."]],
                "",
                "## References",
                *[f"- {item}" for item in self.references or ["No references recorded."]],
            ]
        )
        return "\n".join(lines) + "\n"


class ResearchReportGenerator:
    def generate(
        self,
        *,
        title: str,
        chat_session: ChatSession | None = None,
        chat_messages: list[ChatMessage] | None = None,
        compare_session: CompareSessionRecord | None = None,
        evidence_records: list[EvidenceHistoryRecord] | None = None,
        bookmarks: list[Bookmark] | None = None,
        highlights: list[Highlight] | None = None,
    ) -> ResearchReport:
        messages = chat_messages or []
        evidence = evidence_records or []
        summary = self._summary(messages, compare_session)
        key_findings = self._key_findings(messages, compare_session, bookmarks or [], highlights or [])
        contradictions = self._contradictions(compare_session)
        open_questions = [message.question for message in messages[-5:] if "?" in message.question]
        references = self._references(messages, bookmarks or [], highlights or [])
        return ResearchReport(
            title=title or (chat_session.title if chat_session else "Research Report"),
            summary=summary,
            key_findings=key_findings,
            evidence=[
                {
                    "query": item.query,
                    "chunk_id": item.chunk_id,
                    "rank": item.rank,
                    "similarity_score": item.similarity_score,
                    "confidence_score": item.confidence_score,
                    "created_at": item.created_at,
                }
                for item in evidence
            ],
            contradictions=contradictions,
            open_questions=open_questions,
            references=references,
        )

    def _summary(self, messages: list[ChatMessage], compare_session: CompareSessionRecord | None) -> str:
        if compare_session is not None:
            return f"Comparison: {compare_session.session_name}. Query: {compare_session.query}"
        if messages:
            return messages[-1].answer[:800]
        return "Research findings assembled from available evidence, bookmarks, and highlights."

    def _key_findings(
        self,
        messages: list[ChatMessage],
        compare_session: CompareSessionRecord | None,
        bookmarks: list[Bookmark],
        highlights: list[Highlight],
    ) -> list[str]:
        findings: list[str] = []
        for message in messages[-3:]:
            findings.append(f"Answered: {message.question}")
        if compare_session is not None:
            findings.append(f"Compared videos for: {compare_session.query}")
        findings.extend(f"Bookmark: {bookmark.title}" for bookmark in bookmarks[:5])
        findings.extend(f"Highlight: {highlight.highlighted_text[:120]}" for highlight in highlights[:5])
        return findings

    def _contradictions(self, compare_session: CompareSessionRecord | None) -> list[str]:
        if compare_session is None:
            return []
        try:
            payload = json.loads(compare_session.result_json)
        except json.JSONDecodeError:
            return []
        return [
            str(item.get("summary", item.get("title", "")))
            for item in payload.get("contradictions", [])
            if isinstance(item, dict)
        ]

    def _references(
        self,
        messages: list[ChatMessage],
        bookmarks: list[Bookmark],
        highlights: list[Highlight],
    ) -> list[str]:
        references: list[str] = []
        for message in messages:
            references.append(f"Chat message `{message.id}` via {message.provider}")
        references.extend(f"Bookmark `{bookmark.id}` at {bookmark.timestamp:.1f}s" for bookmark in bookmarks)
        references.extend(f"Highlight `{highlight.id}` at {highlight.timestamp:.1f}s" for highlight in highlights)
        return references

