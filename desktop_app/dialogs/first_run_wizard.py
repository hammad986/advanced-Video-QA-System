from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)

from desktop_app.providers.provider_health import ProviderHealthService
from desktop_app.providers.provider_manager import ProviderManager
from desktop_app.providers.provider_profile import ProviderName
from desktop_app.settings.settings_manager import SettingsManager


class FirstRunWizard(QWizard):
    def __init__(
        self,
        *,
        settings_manager: SettingsManager,
        provider_manager: ProviderManager,
        provider_health_service: ProviderHealthService | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.provider_manager = provider_manager
        self.provider_health_service = provider_health_service
        self.setWindowTitle("Welcome to Advanced Video QA Pro")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.resize(720, 520)
        self.project_page = ProjectFolderPage(settings_manager.current.workspace_path)
        self.provider_page = ProviderSetupPage(provider_manager)
        self.runtime_page = RuntimeProfilePage(settings_manager.current.performance_mode)
        self.validation_page = SystemValidationPage(provider_health_service)
        self.addPage(WelcomePage())
        self.addPage(self.project_page)
        self.addPage(self.provider_page)
        self.addPage(self.runtime_page)
        self.addPage(self.validation_page)
        self.addPage(ReadyPage())

    def accept(self) -> None:
        selected_provider = self.provider_page.provider_name()
        if selected_provider is not None and self.provider_page.should_save_provider():
            definition = self.provider_manager.registry.get(selected_provider)
            self.provider_manager.create_provider(
                selected_provider,
                api_key=self.provider_page.api_key(),
                base_url=self.provider_page.base_url() or definition.default_base_url,
                model=self.provider_page.model() or definition.default_model,
                embedding_model=definition.default_embedding_model,
                enabled=True,
            )
        self.settings_manager.update(
            workspace_path=self.project_page.project_folder(),
            performance_mode=self.runtime_page.runtime_profile(),
            low_memory_mode=self.runtime_page.runtime_profile() == "low_memory",
            first_run_completed=True,
        )
        super().accept()


class WelcomePage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Welcome")
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Advanced Video QA Pro runs locally on your Windows machine. "
                "This wizard configures your workspace, provider, runtime profile, and validation checks."
            )
        )


class ProjectFolderPage(QWizardPage):
    def __init__(self, default_path: str) -> None:
        super().__init__()
        self.setTitle("Select Project Folder")
        self.folder_input = QLineEdit(default_path)
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse)
        layout = QFormLayout(self)
        layout.addRow("Project Folder", self.folder_input)
        layout.addRow("", browse_button)

    def browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Project Folder", self.folder_input.text())
        if folder:
            self.folder_input.setText(folder)

    def project_folder(self) -> str:
        return str(Path(self.folder_input.text()).expanduser())


class ProviderSetupPage(QWizardPage):
    def __init__(self, provider_manager: ProviderManager) -> None:
        super().__init__()
        self.setTitle("Configure Provider")
        self.provider_manager = provider_manager
        self.provider_combo = QComboBox()
        self.provider_combo.addItem("Skip for now", "")
        for definition in provider_manager.registry.all():
            self.provider_combo.addItem(definition.display_name, definition.name.value)
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.base_url_input = QLineEdit()
        self.model_input = QLineEdit()
        self.provider_combo.currentIndexChanged.connect(self.apply_defaults)
        layout = QFormLayout(self)
        layout.addRow("Provider", self.provider_combo)
        layout.addRow("API Key", self.api_key_input)
        layout.addRow("Base URL", self.base_url_input)
        layout.addRow("Model", self.model_input)

    def apply_defaults(self) -> None:
        provider_name = self.provider_name()
        if provider_name is None:
            self.base_url_input.clear()
            self.model_input.clear()
            return
        definition = self.provider_manager.registry.get(provider_name)
        self.base_url_input.setText(definition.default_base_url)
        self.model_input.setText(definition.default_model)

    def should_save_provider(self) -> bool:
        return self.provider_name() is not None

    def provider_name(self) -> ProviderName | None:
        value = str(self.provider_combo.currentData() or "")
        return ProviderName(value) if value else None

    def api_key(self) -> str:
        return self.api_key_input.text().strip()

    def base_url(self) -> str:
        return self.base_url_input.text().strip()

    def model(self) -> str:
        return self.model_input.text().strip()


class RuntimeProfilePage(QWizardPage):
    def __init__(self, current_profile: str) -> None:
        super().__init__()
        self.setTitle("Choose Runtime Profile")
        self.profile_combo = QComboBox()
        for label, value in (
            ("Automatic", "auto"),
            ("Low Memory", "low_memory"),
            ("Balanced", "balanced"),
            ("Performance", "performance"),
        ):
            self.profile_combo.addItem(label, value)
        index = self.profile_combo.findData(current_profile)
        self.profile_combo.setCurrentIndex(index if index >= 0 else 0)
        layout = QFormLayout(self)
        layout.addRow("Runtime Profile", self.profile_combo)

    def runtime_profile(self) -> str:
        return str(self.profile_combo.currentData())


class SystemValidationPage(QWizardPage):
    def __init__(self, provider_health_service: ProviderHealthService | None) -> None:
        super().__init__()
        self.setTitle("System Validation")
        self.provider_health_service = provider_health_service
        self.results = QTextEdit()
        self.results.setReadOnly(True)
        run_button = QPushButton("Run Validation")
        run_button.clicked.connect(self.run_validation)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Run a non-sensitive provider and system validation before finishing setup."))
        layout.addWidget(self.results, 1)
        layout.addWidget(run_button)

    def run_validation(self) -> None:
        if self.provider_health_service is None:
            self.results.setPlainText("Provider health service is unavailable.")
            return
        results = self.provider_health_service.check_all(include_env=False)
        self.results.setPlainText(
            "\n".join(f"{result.provider.value}: {result.status.value} ({result.latency_ms:.0f} ms)" for result in results)
        )


class ReadyPage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Ready")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Setup is complete. You can now create a research project and import videos."))
