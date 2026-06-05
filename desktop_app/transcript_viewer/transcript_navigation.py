from __future__ import annotations

from desktop_app.transcripts.transcript_models import TranscriptSegment


def seconds_to_milliseconds(seconds: float) -> int:
    return max(0, int(seconds * 1000))


def find_active_segment_index(segments: list[TranscriptSegment], position_ms: int) -> int | None:
    position_seconds = position_ms / 1000.0
    low = 0
    high = len(segments) - 1
    while low <= high:
        mid = (low + high) // 2
        segment = segments[mid]
        if segment.start_time <= position_seconds <= segment.end_time:
            return mid
        if position_seconds < segment.start_time:
            high = mid - 1
        else:
            low = mid + 1
    if 0 <= high < len(segments):
        return high
    return None


def format_timestamp(seconds: float) -> str:
    total_seconds = max(0, int(seconds))
    secs = total_seconds % 60
    mins = (total_seconds // 60) % 60
    hours = total_seconds // 3600
    if hours:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"

