from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QGroupBox, QLabel, QVBoxLayout, QWidget

from desktop_app.performance.hardware_profiles import HardwareProfile
from desktop_app.performance.memory_monitor import MemoryMonitor


class MemoryDashboardWidget(QGroupBox):
    def __init__(
        self,
        memory_monitor: MemoryMonitor,
        hardware_profile: HardwareProfile,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Memory Dashboard", parent)
        self.memory_monitor = memory_monitor
        self.hardware_profile = hardware_profile
        self.ram_label = QLabel()
        self.peak_label = QLabel()
        self.models_label = QLabel()
        self.estimate_label = QLabel()
        self.pipeline_label = QLabel()
        self.profile_label = QLabel()

        layout = QVBoxLayout(self)
        layout.addWidget(self.profile_label)
        layout.addWidget(self.ram_label)
        layout.addWidget(self.peak_label)
        layout.addWidget(self.models_label)
        layout.addWidget(self.estimate_label)
        layout.addWidget(self.pipeline_label)

        self.timer = QTimer(self)
        self.timer.setInterval(5000)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()
        self.refresh()

    def refresh(self) -> None:
        snapshot = self.memory_monitor.snapshot()
        self.profile_label.setText(
            f"Profile: {self.hardware_profile.name} · {self.hardware_profile.ram_gb:.1f} GB RAM"
        )
        self.ram_label.setText(f"Current RAM: {snapshot.current_ram_mb:.1f} MB")
        self.peak_label.setText(f"Peak RAM: {snapshot.peak_ram_mb:.1f} MB")
        self.models_label.setText(
            f"Loaded Models: {snapshot.loaded_models}"
            f"{' · ' + ', '.join(snapshot.model_names) if snapshot.model_names else ''}"
        )
        self.estimate_label.setText(f"Model Estimate: {snapshot.model_memory_estimate_mb:.1f} MB")
        self.pipeline_label.setText(f"Pipeline: {snapshot.pipeline_status}")
