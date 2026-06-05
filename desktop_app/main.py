from __future__ import annotations

import os
import sys
import json
from pathlib import Path


def _bootstrap_import_path() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


def main() -> int:
    _bootstrap_import_path()

    import multiprocessing

    from desktop_app.core.frozen_runtime import configure_frozen_runtime_paths

    configure_frozen_runtime_paths()
    multiprocessing.freeze_support()

    selftest_result = _run_transcription_selftest_if_requested()
    if selftest_result is not None:
        return selftest_result

    from PySide6.QtWidgets import QApplication

    from desktop_app.app import AdvancedVideoQAApp
    from desktop_app.core.app_paths import AppPaths
    from desktop_app.core.logging_config import configure_logging

    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

    paths = AppPaths.resolve()
    configure_logging(paths)

    qt_app = QApplication(sys.argv)
    desktop_app = AdvancedVideoQAApp(qt_app, paths)
    desktop_app.start()
    return qt_app.exec()


def _run_transcription_selftest_if_requested() -> int | None:
    video_path_text = os.environ.get("ADVANCED_VIDEO_QA_TRANSCRIPTION_SELFTEST_VIDEO")
    if not video_path_text:
        return None

    from desktop_app.core.frozen_runtime import configure_frozen_runtime_paths
    from desktop_app.transcripts.transcription_worker import CancellationToken
    from desktop_app.workers.transcription_process import ProcessTranscriptionWorker

    configure_frozen_runtime_paths()
    output_path = Path(os.environ.get("ADVANCED_VIDEO_QA_TRANSCRIPTION_SELFTEST_OUTPUT", "transcription_selftest.json"))
    model_name = os.environ.get("ADVANCED_VIDEO_QA_TRANSCRIPTION_SELFTEST_MODEL", "tiny")
    progress_events: list[dict[str, object]] = []

    def progress(percent: int, message: str) -> None:
        progress_events.append({"percent": percent, "message": message})

    try:
        result = ProcessTranscriptionWorker(model_name=model_name, max_restarts=0).run(
            Path(video_path_text),
            CancellationToken(),
            progress,
        )
        payload = {
            "ok": True,
            "model": model_name,
            "language": result.language,
            "segment_count": len(result.segments),
            "first_segment": result.segments[0].text if result.segments else "",
            "progress": progress_events,
        }
        exit_code = 0
    except Exception as exc:
        payload = {
            "ok": False,
            "model": model_name,
            "error_class": exc.__class__.__name__,
            "error": str(exc),
            "progress": progress_events,
        }
        exit_code = 2
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
