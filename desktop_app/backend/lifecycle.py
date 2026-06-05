from __future__ import annotations

import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)


class BackendLifecycle:
    def __init__(self) -> None:
        self._startup_steps: list[Callable[[], None]] = []
        self._shutdown_steps: list[Callable[[], None]] = []
        self._cleanup_steps: list[Callable[[], None]] = []

    def add_startup_step(self, step: Callable[[], None]) -> None:
        self._startup_steps.append(step)

    def add_shutdown_step(self, step: Callable[[], None]) -> None:
        self._shutdown_steps.append(step)

    def add_cleanup_step(self, step: Callable[[], None]) -> None:
        self._cleanup_steps.append(step)

    def startup(self) -> None:
        logger.info("Backend runtime startup sequence started")
        for step in self._startup_steps:
            step()
        logger.info("Backend runtime startup sequence completed")

    def shutdown(self) -> None:
        logger.info("Backend runtime shutdown sequence started")
        for step in reversed(self._shutdown_steps):
            step()
        logger.info("Backend runtime shutdown sequence completed")

    def cleanup(self) -> None:
        logger.info("Backend runtime cleanup sequence started")
        for step in reversed(self._cleanup_steps):
            step()
        logger.info("Backend runtime cleanup sequence completed")

