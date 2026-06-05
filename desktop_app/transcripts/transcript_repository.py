from __future__ import annotations

from sqlite3 import Row

from desktop_app.database.connection import DatabaseConnection
from desktop_app.transcripts.transcript_models import (
    Transcript,
    TranscriptSegment,
    TranscriptStatus,
)


class TranscriptRepository:
    def __init__(self, connection: DatabaseConnection) -> None:
        self.connection = connection

    def save_transcript(self, transcript: Transcript) -> Transcript:
        with self.connection.connect() as connection:
            connection.execute(
                """
                INSERT INTO transcripts (id, video_id, language, model_name, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    language = excluded.language,
                    model_name = excluded.model_name,
                    status = excluded.status
                """,
                (
                    transcript.id,
                    transcript.video_id,
                    transcript.language,
                    transcript.model_name,
                    transcript.status.value,
                    transcript.created_at,
                ),
            )
        return transcript

    def update_status(
        self,
        transcript_id: str,
        status: TranscriptStatus,
        *,
        language: str | None = None,
    ) -> None:
        if language is None:
            with self.connection.connect() as connection:
                connection.execute(
                    "UPDATE transcripts SET status = ? WHERE id = ?",
                    (status.value, transcript_id),
                )
            return
        with self.connection.connect() as connection:
            connection.execute(
                "UPDATE transcripts SET status = ?, language = ? WHERE id = ?",
                (status.value, language, transcript_id),
            )

    def replace_segments(self, transcript_id: str, segments: list[TranscriptSegment]) -> None:
        with self.connection.connect() as connection:
            connection.execute("DELETE FROM transcript_segments WHERE transcript_id = ?", (transcript_id,))
            connection.executemany(
                """
                INSERT INTO transcript_segments (
                    id, transcript_id, start_time, end_time, text, confidence
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        segment.id,
                        segment.transcript_id,
                        segment.start_time,
                        segment.end_time,
                        segment.text,
                        segment.confidence,
                    )
                    for segment in segments
                ],
            )

    def get_transcript(self, transcript_id: str) -> Transcript | None:
        with self.connection.connect() as connection:
            row = connection.execute("SELECT * FROM transcripts WHERE id = ?", (transcript_id,)).fetchone()
        return self._row_to_transcript(row) if row is not None else None

    def list_by_video(self, video_id: str) -> list[Transcript]:
        with self.connection.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM transcripts WHERE video_id = ? ORDER BY created_at DESC",
                (video_id,),
            ).fetchall()
        return [self._row_to_transcript(row) for row in rows]

    def list_segments(self, transcript_id: str) -> list[TranscriptSegment]:
        with self.connection.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM transcript_segments WHERE transcript_id = ? ORDER BY start_time ASC",
                (transcript_id,),
            ).fetchall()
        return [self._row_to_segment(row) for row in rows]

    def _row_to_transcript(self, row: Row) -> Transcript:
        return Transcript(
            id=str(row["id"]),
            video_id=str(row["video_id"]),
            language=str(row["language"] or ""),
            model_name=str(row["model_name"]),
            status=TranscriptStatus(str(row["status"])),
            created_at=float(row["created_at"]),
        )

    def _row_to_segment(self, row: Row) -> TranscriptSegment:
        return TranscriptSegment(
            id=str(row["id"]),
            transcript_id=str(row["transcript_id"]),
            start_time=float(row["start_time"]),
            end_time=float(row["end_time"]),
            text=str(row["text"]),
            confidence=float(row["confidence"]),
        )

