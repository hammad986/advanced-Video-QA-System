from __future__ import annotations

import re
from collections import defaultdict

from desktop_app.compare.compare_models import (
    CompareFinding,
    CompareFindingType,
    CompareResult,
    CompareTopic,
)
from desktop_app.evidence.evidence_models import EvidenceItem
from desktop_app.videos.video_model import VideoRecord


class CompareEngine:
    CONTRADICTION_PAIRS = (
        ("supervised", "unsupervised"),
        ("labeled", "unlabeled"),
        ("classification", "clustering"),
        ("requires labels", "without labels"),
        ("parametric", "nonparametric"),
    )

    def build_result(
        self,
        *,
        project_id: str,
        session_name: str,
        query: str,
        videos: list[VideoRecord],
        evidence_items: list[EvidenceItem],
        topics_by_video: dict[str, list[CompareTopic]],
        duration_ms: float,
        created_at: float,
    ) -> CompareResult:
        video_ids = [video.id for video in videos]
        return CompareResult(
            project_id=project_id,
            session_name=session_name,
            video_ids=video_ids,
            query=query,
            video_sources=videos,
            agreements=self._agreements(videos, topics_by_video, evidence_items),
            differences=self._differences(videos, topics_by_video, evidence_items),
            unique_concepts=self._unique_concepts(videos, topics_by_video, evidence_items),
            missing_topics=self._missing_topics(videos, topics_by_video, evidence_items),
            contradictions=self._contradictions(videos, topics_by_video, evidence_items),
            timeline_differences=self._timeline_differences(videos, topics_by_video, evidence_items),
            evidence_items=evidence_items,
            duration_ms=duration_ms,
            created_at=created_at,
        )

    def _agreements(
        self,
        videos: list[VideoRecord],
        topics_by_video: dict[str, list[CompareTopic]],
        evidence_items: list[EvidenceItem],
    ) -> list[CompareFinding]:
        by_topic = self._topic_video_map(topics_by_video)
        findings: list[CompareFinding] = []
        for topic, video_ids in by_topic.items():
            if len(video_ids) < 2:
                continue
            evidence = self._evidence_for_topic(topic, evidence_items)
            findings.append(
                CompareFinding(
                    finding_type=CompareFindingType.AGREEMENT,
                    title=f"Shared topic: {topic}",
                    summary=f"{len(video_ids)} videos cover {topic}.",
                    video_ids=sorted(video_ids),
                    evidence_items=evidence,
                    confidence=self._average_confidence(evidence),
                )
            )
        return self._limit(findings)

    def _differences(
        self,
        videos: list[VideoRecord],
        topics_by_video: dict[str, list[CompareTopic]],
        evidence_items: list[EvidenceItem],
    ) -> list[CompareFinding]:
        all_topics = set(self._topic_video_map(topics_by_video))
        findings: list[CompareFinding] = []
        for video in videos:
            video_topics = {self._normalize_topic(topic.topic_title) for topic in topics_by_video.get(video.id, [])}
            different = sorted(all_topics - video_topics)
            if not different:
                continue
            findings.append(
                CompareFinding(
                    finding_type=CompareFindingType.DIFFERENCE,
                    title=f"{video.name} differs in topic coverage",
                    summary=f"Compared with the selected set, this video does not cover: {', '.join(different[:5])}.",
                    video_ids=[video.id],
                    evidence_items=[item for item in evidence_items if item.source.video_id == video.id],
                    confidence=0.7,
                )
            )
        return findings

    def _unique_concepts(
        self,
        videos: list[VideoRecord],
        topics_by_video: dict[str, list[CompareTopic]],
        evidence_items: list[EvidenceItem],
    ) -> list[CompareFinding]:
        by_topic = self._topic_video_map(topics_by_video)
        names = {video.id: video.name for video in videos}
        findings: list[CompareFinding] = []
        for topic, video_ids in by_topic.items():
            if len(video_ids) != 1:
                continue
            video_id = next(iter(video_ids))
            evidence = self._evidence_for_topic(topic, evidence_items, video_id=video_id)
            findings.append(
                CompareFinding(
                    finding_type=CompareFindingType.UNIQUE_CONCEPT,
                    title=f"Unique to {names.get(video_id, video_id)}: {topic}",
                    summary=f"{topic} appears only in {names.get(video_id, video_id)} among the selected videos.",
                    video_ids=[video_id],
                    evidence_items=evidence,
                    confidence=self._average_confidence(evidence) or 0.65,
                )
            )
        return self._limit(findings)

    def _missing_topics(
        self,
        videos: list[VideoRecord],
        topics_by_video: dict[str, list[CompareTopic]],
        evidence_items: list[EvidenceItem],
    ) -> list[CompareFinding]:
        by_topic = self._topic_video_map(topics_by_video)
        all_video_ids = {video.id for video in videos}
        names = {video.id: video.name for video in videos}
        findings: list[CompareFinding] = []
        for topic, covered_ids in by_topic.items():
            missing_ids = sorted(all_video_ids - covered_ids)
            if not missing_ids or len(covered_ids) == 1:
                continue
            findings.append(
                CompareFinding(
                    finding_type=CompareFindingType.MISSING_TOPIC,
                    title=f"Missing topic: {topic}",
                    summary=f"{topic} is missing from {', '.join(names.get(video_id, video_id) for video_id in missing_ids)}.",
                    video_ids=missing_ids,
                    evidence_items=self._evidence_for_topic(topic, evidence_items),
                    confidence=0.72,
                )
            )
        return self._limit(findings)

    def _contradictions(
        self,
        videos: list[VideoRecord],
        topics_by_video: dict[str, list[CompareTopic]],
        evidence_items: list[EvidenceItem],
    ) -> list[CompareFinding]:
        text_by_video = {
            video_id: " ".join(topic.chunk_text.lower() for topic in topics)
            for video_id, topics in topics_by_video.items()
        }
        findings: list[CompareFinding] = []
        for left, right in self.CONTRADICTION_PAIRS:
            left_videos = {video_id for video_id, text in text_by_video.items() if left in text}
            right_videos = {video_id for video_id, text in text_by_video.items() if right in text}
            if left_videos and right_videos and left_videos != right_videos:
                involved = sorted(left_videos | right_videos)
                findings.append(
                    CompareFinding(
                        finding_type=CompareFindingType.CONTRADICTION,
                        title=f"Potential contrast: {left} vs {right}",
                        summary=f"Selected videos contain contrasting terminology: {left} and {right}.",
                        video_ids=involved,
                        evidence_items=[
                            item
                            for item in evidence_items
                            if item.source.video_id in involved
                            and (left in item.chunk_text.lower() or right in item.chunk_text.lower())
                        ],
                        confidence=0.55,
                    )
                )
        return self._limit(findings)

    def _timeline_differences(
        self,
        videos: list[VideoRecord],
        topics_by_video: dict[str, list[CompareTopic]],
        evidence_items: list[EvidenceItem],
    ) -> list[CompareFinding]:
        topic_times: dict[str, dict[str, float]] = defaultdict(dict)
        for video_id, topics in topics_by_video.items():
            for topic in topics:
                normalized = self._normalize_topic(topic.topic_title)
                old = topic_times[normalized].get(video_id)
                if old is None or topic.start_time < old:
                    topic_times[normalized][video_id] = topic.start_time
        findings: list[CompareFinding] = []
        for topic, times in topic_times.items():
            if len(times) < 2:
                continue
            spread = max(times.values()) - min(times.values())
            if spread < 15:
                continue
            details = ", ".join(f"{self._video_name(videos, video_id)} at {start:.1f}s" for video_id, start in times.items())
            findings.append(
                CompareFinding(
                    finding_type=CompareFindingType.TIMELINE_DIFFERENCE,
                    title=f"Timeline shift: {topic}",
                    summary=f"{topic} appears at different points: {details}.",
                    video_ids=sorted(times),
                    evidence_items=self._evidence_for_topic(topic, evidence_items),
                    confidence=0.68,
                )
            )
        return self._limit(findings)

    def _topic_video_map(self, topics_by_video: dict[str, list[CompareTopic]]) -> dict[str, set[str]]:
        by_topic: dict[str, set[str]] = defaultdict(set)
        for video_id, topics in topics_by_video.items():
            for topic in topics:
                normalized = self._normalize_topic(topic.topic_title)
                if normalized:
                    by_topic[normalized].add(video_id)
        return by_topic

    def _evidence_for_topic(
        self,
        topic: str,
        evidence_items: list[EvidenceItem],
        *,
        video_id: str | None = None,
    ) -> list[EvidenceItem]:
        topic_terms = self._terms(topic)
        matches: list[EvidenceItem] = []
        for item in evidence_items:
            if video_id is not None and item.source.video_id != video_id:
                continue
            item_terms = self._terms(f"{item.topic_title} {item.chunk_text}")
            if topic_terms & item_terms:
                matches.append(item)
        return matches[:6]

    def _average_confidence(self, evidence_items: list[EvidenceItem]) -> float:
        if not evidence_items:
            return 0.0
        return sum(item.confidence_score for item in evidence_items) / len(evidence_items)

    def _normalize_topic(self, topic: str) -> str:
        normalized = re.sub(r"\s+", " ", topic.strip().lower())
        return normalized or "untitled topic"

    def _terms(self, text: str) -> set[str]:
        return {
            term
            for term in re.findall(r"[a-z0-9]+", text.lower())
            if len(term) > 2 and term not in {"the", "and", "for", "with", "what", "how", "why", "this", "that"}
        }

    def _video_name(self, videos: list[VideoRecord], video_id: str) -> str:
        for video in videos:
            if video.id == video_id:
                return video.name
        return video_id

    def _limit(self, findings: list[CompareFinding], limit: int = 10) -> list[CompareFinding]:
        return sorted(findings, key=lambda finding: finding.confidence, reverse=True)[:limit]
