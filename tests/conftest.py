from __future__ import annotations

import os
import sys
from collections.abc import Iterator

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
except ImportError:  # pragma: no cover - dependency validation catches this in Sprint 1.
    QApplication = None  # type: ignore[assignment]


@pytest.fixture(scope="session")
def qapp() -> Iterator[QApplication]:
    if QApplication is None:
        pytest.skip("PySide6 is not installed")
    app = QApplication.instance() or QApplication(sys.argv)
    yield app

