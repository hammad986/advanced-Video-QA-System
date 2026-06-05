from __future__ import annotations

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, Signal
from PySide6.QtWidgets import QLabel, QListView, QPlainTextEdit, QVBoxLayout, QWidget

from desktop_app.compare.compare_models import CompareFinding, CompareResult
from desktop_app.evidence.evidence_models import EvidenceItem
from desktop_app.transcript_viewer.transcript_navigation import format_timestamp


class CompareEvidenceListModel(QAbstractListModel):
    def __init__(self) -> None:
        super().__init__()
        self.items: list[EvidenceItem] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self.items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid() or not 0 <= index.row() < len(self.items):
            return None
        item = self.items[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            timestamp = f"{format_timestamp(item.start_time)} - {format_timestamp(item.end_time)}"
            return (
                f"{item.source.video_name} · {item.topic_title}\n"
                f"{timestamp} · confidence {item.confidence_score:.3f}\n"
                f"{item.chunk_text}"
            )
        if role == Qt.ItemDataRole.UserRole:
            return item
        return None

    def set_items(self, items: list[EvidenceItem]) -> None:
        self.beginResetModel()
        self.items = items
        self.endResetModel()


class CompareResultView(QWidget):
    evidence_selected = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.status_label = QLabel("No comparison result")
        self.summary_output = QPlainTextEdit()
        self.summary_output.setReadOnly(True)
        self.summary_output.setPlaceholderText("Comparison results will appear here.")
        self.evidence_model = CompareEvidenceListModel()
        self.evidence_view = QListView()
        self.evidence_view.setModel(self.evidence_model)
        self.evidence_view.setUniformItemSizes(False)
        self.evidence_view.clicked.connect(self._emit_evidence_selected)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.status_label)
        layout.addWidget(self.summary_output, 2)
        layout.addWidget(QLabel("Evidence"))
        layout.addWidget(self.evidence_view, 1)

    def set_result(self, result: CompareResult) -> None:
        finding_count = sum(
            len(findings)
            for findings in (
                result.agreements,
                result.differences,
                result.unique_concepts,
                result.missing_topics,
                result.contradictions,
                result.timeline_differences,
            )
        )
        self.status_label.setText(
            f"{finding_count:,} findings · {len(result.evidence_items):,} evidence items · {result.duration_ms:.1f} ms"
        )
        self.summary_output.setPlainText(self._format_result(result))
        self.evidence_model.set_items(result.evidence_items)

    def clear(self) -> None:
        self.status_label.setText("No comparison result")
        self.summary_output.clear()
        self.evidence_model.set_items([])

    def _format_result(self, result: CompareResult) -> str:
        lines = [
            f"Query: {result.query}",
            "Videos:",
            *[f"- {video.name}" for video in result.video_sources],
            "",
        ]
        sections = (
            ("Agreements", result.agreements),
            ("Differences", result.differences),
            ("Unique Concepts", result.unique_concepts),
            ("Missing Topics", result.missing_topics),
            ("Contradictions", result.contradictions),
            ("Timeline Differences", result.timeline_differences),
        )
        for title, findings in sections:
            lines.append(title)
            if not findings:
                lines.append("- None detected")
            for finding in findings:
                lines.extend(self._format_finding(finding))
            lines.append("")
        return "\n".join(lines).strip()

    def _format_finding(self, finding: CompareFinding) -> list[str]:
        return [
            f"- {finding.title}",
            f"  {finding.summary}",
            f"  Confidence: {finding.confidence:.3f}; evidence: {len(finding.evidence_items)}",
        ]

    def _emit_evidence_selected(self, index: QModelIndex) -> None:
        item = self.evidence_model.data(index, Qt.ItemDataRole.UserRole)
        if isinstance(item, EvidenceItem):
            self.evidence_selected.emit(item)
