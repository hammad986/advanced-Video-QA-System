from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGroupBox, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget

from desktop_app.diagnostics.diagnostics_service import DiagnosticsSnapshot


class DiagnosticsPanelWidget(QGroupBox):
    refresh_requested = Signal()
    export_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Diagnostics Center", parent)
        self.summary = QTextEdit()
        self.summary.setReadOnly(True)
        self.refresh_button = QPushButton("Refresh Diagnostics")
        self.export_button = QPushButton("Export Diagnostics Report")
        self.refresh_button.clicked.connect(self.refresh_requested.emit)
        self.export_button.clicked.connect(self.export_requested.emit)
        self.status_label = QLabel("Diagnostics not captured yet.")
        layout = QVBoxLayout(self)
        layout.addWidget(self.status_label)
        layout.addWidget(self.summary, 1)
        layout.addWidget(self.refresh_button)
        layout.addWidget(self.export_button)

    def set_snapshot(self, snapshot: DiagnosticsSnapshot) -> None:
        self.status_label.setText("Diagnostics captured.")
        providers = ", ".join(f"{name}: {status}" for name, status in snapshot.provider_status.items()) or "None"
        self.summary.setPlainText(
            "\n".join(
                [
                    f"Platform: {snapshot.platform_summary}",
                    f"CPU: {snapshot.cpu_percent:.1f}%",
                    f"RAM: {snapshot.ram_used_mb:.1f} / {snapshot.ram_total_mb:.1f} MB ({snapshot.ram_percent:.1f}%)",
                    f"GPU: {snapshot.gpu_summary}",
                    f"Workers: {snapshot.worker_status}",
                    f"Providers: {providers}",
                    f"Queues: {snapshot.queue_status}",
                ]
            )
        )
