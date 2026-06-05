from __future__ import annotations

import logging

from .app_paths import AppPaths


def configure_logging(paths: AppPaths) -> None:
    paths.ensure()
    log_path = paths.logs_dir / "desktop_app.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

