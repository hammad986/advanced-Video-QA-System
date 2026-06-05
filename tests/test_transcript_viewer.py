from __future__ import annotations

import json

from PySide6.QtCore import Qt

from desktop_app.transcript_viewer.transcript_exporter import TranscriptExporter
from desktop_app.transcript_viewer.transcript_navigation import find_active_segment_index, format_timestamp
from desktop_app.transcript_viewer.transcript_search import TranscriptSearchEngine
from desktop_app.transcript_viewer.transcript_viewer_widget import TranscriptViewerWidget
from desktop_app.transcripts.transcript_models import (
    Transcript,
    TranscriptSegment,
    TranscriptStatus,
)


def _transcript() -> Transcript:
    return Transcript.create(
        video_id="video-1",
        model_name="base",
        language="en",
        status=TranscriptStatus.COMPLETED,
    )


def _segments(count: int = 5) -> list[TranscriptSegment]:
    return [
        TranscriptSegment.create(
            transcript_id="transcript-1",
            start_time=float(index * 2),
            end_time=float(index * 2 + 1.5),
            text=f"Segment {index} research keyword" if index % 2 == 0 else f"Segment {index} plain text",
            confidence=0.75 + (index % 10) / 100,
        )
        for index in range(count)
    ]


def test_transcript_search_next_previous() -> None:
    result = TranscriptSearchEngine().search(_segments(6), "keyword")

    assert result.indices == [0, 2, 4]
    assert TranscriptSearchEngine().next_result(result).current_index == 2
    assert TranscriptSearchEngine().previous_result(result).current_index == 4


def test_transcript_navigation_finds_active_segment() -> None:
    segments = _segments(4)

    assert find_active_segment_index(segments, 2500) == 1
    assert format_timestamp(3661) == "1:01:01"


def test_transcript_viewer_loads_10000_segments_without_eager_widgets(qapp) -> None:
    widget = TranscriptViewerWidget()
    transcript = _transcript()
    segments = _segments(10_000)

    widget.load_transcript(transcript, segments)

    assert widget.model.rowCount() == 10_000
    assert "10,000 segments" in widget.status_label.text()
    assert widget.segment_view.model() is widget.model


def test_transcript_viewer_search_highlights_and_navigation(qapp) -> None:
    widget = TranscriptViewerWidget()
    widget.load_transcript(_transcript(), _segments(6))

    widget.apply_search("keyword")

    assert widget.search_result.indices == [0, 2, 4]
    assert widget.model.search_indices == {0, 2, 4}
    widget.next_result()
    assert widget.segment_view.currentIndex().row() == 2
    widget.previous_result()
    assert widget.segment_view.currentIndex().row() == 0


def test_transcript_viewer_click_emits_seek_timestamp(qapp) -> None:
    widget = TranscriptViewerWidget()
    widget.load_transcript(_transcript(), _segments(3))
    emitted: list[int] = []
    widget.segment_selected.connect(emitted.append)

    widget._emit_segment_selected(widget.model.index(1))

    assert emitted == [2000]


def test_transcript_viewer_auto_follows_playback(qapp) -> None:
    widget = TranscriptViewerWidget()
    widget.load_transcript(_transcript(), _segments(5))

    widget.set_playback_position(4500)

    assert widget.model.active_index == 2
    background = widget.model.data(widget.model.index(2), Qt.ItemDataRole.BackgroundRole)
    assert background is not None


def test_transcript_exporter_outputs_txt_markdown_json(tmp_path) -> None:
    transcript = _transcript()
    segments = _segments(2)
    exporter = TranscriptExporter()

    txt_path = exporter.export_txt(transcript, segments, tmp_path / "transcript.txt")
    md_path = exporter.export_markdown(transcript, segments, tmp_path / "transcript.md")
    json_path = exporter.export_json(transcript, segments, tmp_path / "transcript.json")

    assert "Segment 0" in txt_path.read_text(encoding="utf-8")
    assert "# Transcript" in md_path.read_text(encoding="utf-8")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["language"] == "en"
    assert len(payload["segments"]) == 2
