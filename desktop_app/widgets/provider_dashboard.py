from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from desktop_app.providers.provider_health import ProviderHealthResult
from desktop_app.providers.provider_usage import ProviderUsageSummary
from desktop_app.providers.provider_benchmark import ProviderBenchmarkRepository


class ProviderDashboardWidget(QGroupBox):
    refresh_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Provider Dashboard", parent)
        self.refresh_button = QPushButton("Refresh Health")
        self.refresh_button.clicked.connect(self.refresh_requested.emit)
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            [
                "Provider",
                "Status",
                "Latency",
                "Success",
                "Failure",
                "Usage",
                "Cost",
                "Message",
            ]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        button_row = QHBoxLayout()
        button_row.addWidget(self.refresh_button)
        button_row.addStretch(1)
        layout = QVBoxLayout(self)
        layout.addLayout(button_row)
        layout.addWidget(self.table, 1)

    def set_results(
        self,
        results: list[ProviderHealthResult],
        *,
        usage_summary: ProviderUsageSummary | None = None,
        benchmark_repository: ProviderBenchmarkRepository | None = None,
    ) -> None:
        self.table.setRowCount(len(results))
        usage_by_provider = usage_summary.by_provider if usage_summary else {}
        for row, result in enumerate(results):
            benchmark = benchmark_repository.summarize(provider=result.provider.value) if benchmark_repository else None
            usage = usage_by_provider.get(result.provider.value, {})
            values = [
                result.provider.value,
                result.status.value,
                f"{result.latency_ms:.0f} ms" if result.latency_ms else "—",
                f"{benchmark.success_rate:.0%}" if benchmark and benchmark.samples else "—",
                f"{benchmark.failure_rate:.0%}" if benchmark and benchmark.samples else "—",
                str(int(usage.get("requests", 0))),
                f"${usage.get('cost_usd', 0.0):.4f}",
                result.message,
            ]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
        self.table.resizeColumnsToContents()
