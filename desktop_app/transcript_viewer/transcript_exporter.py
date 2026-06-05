from __future__ import annotations

import json
from pathlib import Path

from desktop_app.transcript_viewer.transcript_navigation import format_timestamp
from desktop_app.transcripts.transcript_models import Transcript, TranscriptSegment


class TranscriptExporter:
    def export_txt(self, transcript: Transcript, segments: list[TranscriptSegment], output_path: Path) -> Path:
        lines = [f"Transcript: {transcript.id}", f"Language: {transcript.language}", ""]
        lines.extend(
            f"[{format_timestamp(segment.start_time)} - {format_timestamp(segment.end_time)}] {segment.text}"
            for segment in segments
        )
        return self._write_text(output_path, "\n".join(lines))

    def export_markdown(self, transcript: Transcript, segments: list[TranscriptSegment], output_path: Path) -> Path:
        lines = [
            "# Transcript",
            "",
            f"- Transcript ID: `{transcript.id}`",
            f"- Language: `{transcript.language}`",
            f"- Model: `{transcript.model_name}`",
            "",
        ]
        lines.extend(
            f"- `[{format_timestamp(segment.start_time)} - {format_timestamp(segment.end_time)}]` {segment.text}"
            for segment in segments
        )
        return self._write_text(output_path, "\n".join(lines))

    def export_json(self, transcript: Transcript, segments: list[TranscriptSegment], output_path: Path) -> Path:
        payload = {
            "id": transcript.id,
            "video_id": transcript.video_id,
            "language": transcript.language,
            "model_name": transcript.model_name,
            "status": transcript.status.value,
            "segments": [
                {
                    "id": segment.id,
                    "start_time": segment.start_time,
                    "end_time": segment.end_time,
                    "text": segment.text,
                    "confidence": segment.confidence,
                }
                for segment in segments
            ],
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return output_path

    def _write_text(self, output_path: Path, text: str) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
        return output_path

