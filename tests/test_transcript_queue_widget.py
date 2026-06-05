from __future__ import annotations

from desktop_app.transcripts.transcript_models import TranscriptJobState, TranscriptStatus
from desktop_app.widgets.transcript_queue import TranscriptQueueWidget


def test_transcript_queue_tracks_progress_and_actions(qapp) -> None:
    widget = TranscriptQueueWidget()
    state = TranscriptJobState(
        job_id="job-1",
        video_id="video-1",
        model_name="base",
        status=TranscriptStatus.RUNNING,
        progress_percent=55,
        error_message="Transcribing",
    )

    widget.add_or_update_job(state)
    widget.queue_list.setCurrentRow(0)

    assert widget.progress_bar.value() == 55
    assert "Running" in widget.status_label.text()
    assert widget.cancel_button.isEnabled() is True
    assert widget.retry_button.isEnabled() is False

    widget.add_or_update_job(
        TranscriptJobState(
            job_id="job-1",
            video_id="video-1",
            model_name="base",
            status=TranscriptStatus.FAILED,
            progress_percent=55,
            error_message="failed",
        )
    )

    assert widget.cancel_button.isEnabled() is False
    assert widget.retry_button.isEnabled() is True
