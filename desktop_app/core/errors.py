from __future__ import annotations


class AppError(Exception):
    """Base user-safe desktop application error."""

    def __init__(self, message: str, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail


class StartupError(AppError):
    """Raised when the desktop application cannot complete startup."""


class ThemeError(AppError):
    """Raised when a theme cannot be loaded or applied."""


class TaskError(AppError):
    """Raised when a background task fails."""

