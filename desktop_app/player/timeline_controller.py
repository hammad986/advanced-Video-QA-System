from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TimelineState:
    position_ms: int = 0
    duration_ms: int = 0

    @property
    def position_label(self) -> str:
        return format_time(self.position_ms)

    @property
    def duration_label(self) -> str:
        return format_time(self.duration_ms)


class TimelineController:
    def __init__(self) -> None:
        self.state = TimelineState()

    def set_duration(self, duration_ms: int) -> TimelineState:
        self.state.duration_ms = max(0, duration_ms)
        self.state.position_ms = min(self.state.position_ms, self.state.duration_ms)
        return self.state

    def set_position(self, position_ms: int) -> TimelineState:
        if self.state.duration_ms > 0:
            self.state.position_ms = max(0, min(position_ms, self.state.duration_ms))
        else:
            self.state.position_ms = max(0, position_ms)
        return self.state

    def seek_ratio(self, ratio: float) -> int:
        ratio = max(0.0, min(ratio, 1.0))
        return int(self.state.duration_ms * ratio)


def format_time(milliseconds: int) -> str:
    total_seconds = max(0, milliseconds) // 1000
    seconds = total_seconds % 60
    minutes = (total_seconds // 60) % 60
    hours = total_seconds // 3600
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"

