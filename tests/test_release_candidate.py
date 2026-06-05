from __future__ import annotations

import json
from pathlib import Path

from desktop_app.database.database_manager import DatabaseManager
from desktop_app.providers.provider_manager import ProviderManager
from desktop_app.providers.provider_profile import ProviderName
from desktop_app.release.installer_audit import InstallerAuditService
from desktop_app.release.provider_generation_validation import ProviderGenerationValidationService
from desktop_app.release.release_candidate_audit import ReleaseCandidateAuditService
from desktop_app.release.update_service import UpdateService, resolve_releases_api_url
from desktop_app.settings.settings_manager import SettingsManager
from desktop_app.settings.settings_repository import SettingsRepository


class FakeCredentialStore:
    def __init__(self) -> None:
        self.secrets: dict[str, str] = {}

    def store_secret(self, target_id: str, secret: str) -> str:
        self.secrets[target_id] = secret
        return f"wincred:test/{target_id}"

    def retrieve_secret(self, stored_reference: str) -> str:
        return self.secrets[stored_reference.rsplit("/", 1)[-1]]

    def delete_secret(self, stored_reference: str) -> None:
        self.secrets.pop(stored_reference.rsplit("/", 1)[-1], None)


class FakeResponse:
    status = 200

    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, _: int) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def provider_stack(tmp_path):
    database = DatabaseManager(tmp_path / "app.db")
    database.initialize()
    settings = SettingsManager(SettingsRepository(database.connection), default_workspace_path=tmp_path / "projects")
    manager = ProviderManager(database.connection, settings, credential_store=FakeCredentialStore())  # type: ignore[arg-type]
    return database, settings, manager


def test_generation_validation_reports_unconfigured_and_restores_default(tmp_path) -> None:
    _, settings, manager = provider_stack(tmp_path)
    validation = ProviderGenerationValidationService(manager, settings)

    results = validation.validate_all()

    assert all(not result.configured for result in results)
    assert settings.current.default_provider == ""


def test_generation_validation_accepts_exact_ok(monkeypatch, tmp_path) -> None:
    _, settings, manager = provider_stack(tmp_path)
    profile = manager.create_provider(ProviderName.OPENAI, api_key="secret", model="gpt-test")

    def fake_generate(self, prompt):  # noqa: ANN001, ANN202
        from desktop_app.answering.answer_service import ProviderGeneration

        assert prompt == "Return exactly: OK"
        return ProviderGeneration(provider="openai", text="OK", model="gpt-test")

    monkeypatch.setattr("desktop_app.answering.answer_service.ProviderExecutor.generate", fake_generate)
    result = ProviderGenerationValidationService(manager, settings).validate_profile(profile)

    assert result.generation_valid is True
    assert result.response_text == "OK"


def test_update_service_compares_versions(monkeypatch) -> None:
    def fake_urlopen(request, timeout):  # noqa: ANN001, ANN202
        assert timeout == 8.0
        return FakeResponse({"tag_name": "v0.2.0", "html_url": "https://example.test/release", "body": "Release notes"})

    monkeypatch.setattr("desktop_app.release.update_service.urlopen", fake_urlopen)
    result = UpdateService(releases_api_url="https://api.example.test/releases/latest", current_version="0.1.0").check_for_update()

    assert result.checked is True
    assert result.update_available is True
    assert result.latest_version == "v0.2.0"
    assert result.release_notes == "Release notes"


def test_update_service_resolves_release_url_from_env_file(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("ADVANCED_VIDEO_QA_RELEASES_API_URL", raising=False)
    env_path = tmp_path / ".env"
    env_path.write_text(
        "OTHER=value\nADVANCED_VIDEO_QA_RELEASES_API_URL=https://api.example.test/releases/latest\n",
        encoding="utf-8",
    )

    assert resolve_releases_api_url(env_path) == "https://api.example.test/releases/latest"


def test_installer_and_release_candidate_audits(tmp_path: Path) -> None:
    icon_dir = tmp_path / "desktop_app" / "resources" / "icons"
    icon_dir.mkdir(parents=True)
    (icon_dir / "app.ico").write_bytes(b"icon")
    database = DatabaseManager(tmp_path / "app.db")
    database.initialize()
    video_dir = tmp_path / "data" / "videos"
    video_dir.mkdir(parents=True)
    (video_dir / "sample.mp4").write_bytes(b"video")

    installer = InstallerAuditService(tmp_path).run()
    release = ReleaseCandidateAuditService(database.connection, video_dir=video_dir).run()

    assert installer.ready is True
    assert release.ready_count == release.total_count
