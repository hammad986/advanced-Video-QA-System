from __future__ import annotations

import json
from pathlib import Path

from desktop_app.database.database_manager import DatabaseManager
from desktop_app.diagnostics.crash_recovery import SessionRecoveryService
from desktop_app.diagnostics.diagnostics_service import DiagnosticsService
from desktop_app.diagnostics.packaging_audit import PackagingAuditService
from desktop_app.providers.provider_health import (
    ProviderHealthRepository,
    ProviderHealthService,
    ProviderHealthStatus,
)
from desktop_app.providers.provider_profile import ProviderName, ProviderProfile
from desktop_app.settings.settings_manager import SettingsManager
from desktop_app.settings.settings_repository import SettingsRepository
from desktop_app.providers.provider_manager import ProviderManager


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


class FakeCredentialStore:
    def __init__(self) -> None:
        self.secrets: dict[str, str] = {}

    def store_secret(self, target_id: str, secret: str) -> str:
        self.secrets[target_id] = secret
        return f"wincred:test/{target_id}"

    def retrieve_secret(self, stored_reference: str) -> str:
        target_id = stored_reference.rsplit("/", 1)[-1]
        return self.secrets[target_id]

    def delete_secret(self, stored_reference: str) -> None:
        target_id = stored_reference.rsplit("/", 1)[-1]
        self.secrets.pop(target_id, None)


def test_provider_health_service_validates_model_and_persists_result(tmp_path, monkeypatch) -> None:
    database = DatabaseManager(tmp_path / "app.db")
    database.initialize()
    repository = ProviderHealthRepository(database.connection)
    service = ProviderHealthService(repository=repository)

    def fake_urlopen(request, timeout):  # noqa: ANN001, ANN202
        assert "Authorization" in request.headers
        assert timeout == service.timeout_seconds
        return FakeResponse({"data": [{"id": "gpt-4o-mini"}]})

    monkeypatch.setattr("desktop_app.providers.provider_health.urlopen", fake_urlopen)
    result = service.check_profile(
        ProviderProfile.create(
            ProviderName.OPENAI,
            api_key="secret",
            base_url="https://api.openai.com/v1",
            model="gpt-4o-mini",
        )
    )

    assert result.status == ProviderHealthStatus.HEALTHY
    assert result.authentication_valid is True
    assert result.model_available is True
    assert repository.list_recent(limit=1)[0].provider == ProviderName.OPENAI


def test_provider_health_service_reports_unconfigured_providers(tmp_path) -> None:
    database = DatabaseManager(tmp_path / "app.db")
    database.initialize()
    settings = SettingsManager(SettingsRepository(database.connection), default_workspace_path=tmp_path / "projects")
    manager = ProviderManager(database.connection, settings, credential_store=FakeCredentialStore())  # type: ignore[arg-type]
    service = ProviderHealthService(
        repository=ProviderHealthRepository(database.connection),
        provider_manager=manager,
        env_path=str(tmp_path / ".env"),
    )

    results = service.check_all(include_env=True)

    assert any(result.provider == ProviderName.OPENAI and not result.configured for result in results)
    assert all(not result.message.lower().startswith("secret") for result in results)


def test_session_recovery_round_trip(tmp_path: Path) -> None:
    service = SessionRecoveryService(tmp_path / "session_recovery.json")
    snapshot = service.create_snapshot(
        project_id="project-1",
        project_name="Project",
        workspace_path="C:/workspace",
        chat_session_id="chat-1",
        video_path="C:/video.mp4",
        video_position_ms=1234,
        layout={"left_width": 320},
    )

    service.save_snapshot(snapshot)
    restored = service.load_snapshot()

    assert restored is not None
    assert restored["project_id"] == "project-1"
    assert restored["video_position_ms"] == 1234


def test_diagnostics_and_packaging_services_export(tmp_path: Path) -> None:
    diagnostics = DiagnosticsService()
    snapshot = diagnostics.capture(worker_status="Workers OK", queue_status="Idle")
    output = diagnostics.export_report(snapshot, tmp_path / "diagnostics.json")

    assert output.exists()
    assert "platform_summary" in output.read_text(encoding="utf-8")
    report = PackagingAuditService().run()
    assert report.checks
