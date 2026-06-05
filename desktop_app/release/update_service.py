from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class UpdateCheckResult:
    checked: bool
    update_available: bool
    current_version: str
    latest_version: str
    release_url: str
    release_notes: str
    message: str


class UpdateService:
    def __init__(self, *, releases_api_url: str, current_version: str, timeout_seconds: float = 8.0) -> None:
        self.releases_api_url = releases_api_url
        self.current_version = current_version
        self.timeout_seconds = timeout_seconds

    def check_for_update(self) -> UpdateCheckResult:
        if not self.releases_api_url:
            return UpdateCheckResult(False, False, self.current_version, "", "", "", "GitHub Releases URL is not configured.")
        request = Request(self.releases_api_url, headers={"User-Agent": "AdvancedVideoQAPro"})
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read(1_000_000).decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            return UpdateCheckResult(
                False,
                False,
                self.current_version,
                "",
                "",
                "",
                f"Update check failed: {type(error).__name__}.",
            )
        latest_version = str(payload.get("tag_name") or payload.get("name") or "").strip()
        release_url = str(payload.get("html_url") or "").strip()
        release_notes = str(payload.get("body") or "").strip()
        update_available = self._is_newer(latest_version, self.current_version)
        return UpdateCheckResult(
            True,
            update_available,
            self.current_version,
            latest_version,
            release_url,
            release_notes,
            "Update available." if update_available else "Application is up to date.",
        )

    def _is_newer(self, latest: str, current: str) -> bool:
        latest_parts = self._version_parts(latest)
        current_parts = self._version_parts(current)
        return latest_parts > current_parts

    def _version_parts(self, value: str) -> tuple[int, ...]:
        parts = [int(part) for part in re.findall(r"\d+", value)]
        return tuple(parts or [0])


def resolve_releases_api_url(env_path: Path | None = None) -> str:
    value = os.environ.get("ADVANCED_VIDEO_QA_RELEASES_API_URL", "").strip()
    if value:
        return value
    path = env_path or Path.cwd() / ".env"
    if not path.exists():
        return ""
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, raw_value = stripped.split("=", 1)
        if key.strip() != "ADVANCED_VIDEO_QA_RELEASES_API_URL":
            continue
        return raw_value.strip().strip('"').strip("'")
    return ""
