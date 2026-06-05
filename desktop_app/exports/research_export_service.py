from __future__ import annotations

import json
from dataclasses import asdict
from enum import StrEnum
from pathlib import Path

from desktop_app.bookmarks.bookmark_repository import BookmarkRepository
from desktop_app.chat.chat_repository import ChatRepository
from desktop_app.compare.compare_repository import CompareRepository
from desktop_app.evidence.evidence_repository import EvidenceRepository
from desktop_app.exports.research_report import ResearchReport, ResearchReportGenerator
from desktop_app.highlights.highlight_repository import HighlightRepository


class ExportFormat(StrEnum):
    PDF = "pdf"
    MARKDOWN = "markdown"
    JSON = "json"


class ResearchExportService:
    def __init__(
        self,
        *,
        chat_repository: ChatRepository,
        compare_repository: CompareRepository,
        evidence_repository: EvidenceRepository,
        bookmark_repository: BookmarkRepository,
        highlight_repository: HighlightRepository,
        report_generator: ResearchReportGenerator | None = None,
    ) -> None:
        self.chat_repository = chat_repository
        self.compare_repository = compare_repository
        self.evidence_repository = evidence_repository
        self.bookmark_repository = bookmark_repository
        self.highlight_repository = highlight_repository
        self.report_generator = report_generator or ResearchReportGenerator()

    def build_project_report(self, project_id: str, *, title: str = "Research Report") -> ResearchReport:
        chat_session = next(iter(self.chat_repository.list_sessions(project_id)), None)
        chat_messages = self.chat_repository.list_messages(chat_session.id) if chat_session else []
        compare_session = next(iter(self.compare_repository.list_sessions(project_id, limit=1)), None)
        return self.report_generator.generate(
            title=title,
            chat_session=chat_session,
            chat_messages=chat_messages,
            compare_session=compare_session,
            evidence_records=self.evidence_repository.list_history(project_id, limit=100),
            bookmarks=self.bookmark_repository.list_by_project(project_id),
            highlights=self.highlight_repository.list_by_project(project_id),
        )

    def export_project_report(
        self,
        project_id: str,
        output_path: Path,
        export_format: ExportFormat,
        *,
        title: str = "Research Report",
    ) -> Path:
        report = self.build_project_report(project_id, title=title)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if export_format == ExportFormat.JSON:
            output_path.write_text(report.to_json(), encoding="utf-8")
        elif export_format == ExportFormat.MARKDOWN:
            output_path.write_text(report.to_markdown(), encoding="utf-8")
        elif export_format == ExportFormat.PDF:
            self._write_pdf(report, output_path)
        else:
            raise ValueError(f"Unsupported export format: {export_format}")
        return output_path

    def export_chat_session(self, session_id: str, output_path: Path, export_format: ExportFormat) -> Path:
        session = self.chat_repository.get_session(session_id)
        if session is None:
            raise ValueError("Chat session was not found.")
        messages = self.chat_repository.list_messages(session_id)
        report = self.report_generator.generate(
            title=session.title,
            chat_session=session,
            chat_messages=messages,
        )
        return self._write_report(report, output_path, export_format)

    def export_compare_session(self, session_id: str, output_path: Path, export_format: ExportFormat) -> Path:
        session = self.compare_repository.get_session(session_id)
        if session is None:
            raise ValueError("Compare session was not found.")
        payload = json.loads(session.result_json)
        report = ResearchReport(
            title=session.session_name,
            summary=f"Comparison query: {session.query}",
            key_findings=[
                *[str(item.get("summary", item.get("title", ""))) for item in payload.get("agreements", [])],
                *[str(item.get("summary", item.get("title", ""))) for item in payload.get("differences", [])],
            ],
            evidence=payload.get("evidence_items", []),
            contradictions=[
                str(item.get("summary", item.get("title", ""))) for item in payload.get("contradictions", [])
            ],
            open_questions=[],
            references=[f"Compare session `{session.id}`"],
        )
        return self._write_report(report, output_path, export_format)

    def _write_report(self, report: ResearchReport, output_path: Path, export_format: ExportFormat) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if export_format == ExportFormat.JSON:
            output_path.write_text(report.to_json(), encoding="utf-8")
        elif export_format == ExportFormat.MARKDOWN:
            output_path.write_text(report.to_markdown(), encoding="utf-8")
        elif export_format == ExportFormat.PDF:
            self._write_pdf(report, output_path)
        else:
            raise ValueError(f"Unsupported export format: {export_format}")
        return output_path

    def _write_pdf(self, report: ResearchReport, output_path: Path) -> None:
        markdown = report.to_markdown()
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
        except ImportError:
            self._write_minimal_pdf(markdown, output_path)
            return
        pdf = canvas.Canvas(str(output_path), pagesize=letter)
        width, height = letter
        y = height - 40
        for raw_line in markdown.splitlines():
            line = raw_line[:110]
            if y < 40:
                pdf.showPage()
                y = height - 40
            pdf.drawString(40, y, line)
            y -= 14
        pdf.save()

    def _write_minimal_pdf(self, text: str, output_path: Path) -> None:
        lines = []
        for raw_line in text.splitlines():
            current = raw_line
            while len(current) > 92:
                lines.append(current[:92])
                current = current[92:]
            lines.append(current)
        page_height = 760
        line_height = 14
        pages = [lines[index : index + 50] for index in range(0, len(lines), 50)] or [[]]
        objects: list[bytes] = [b""]
        page_object_ids: list[int] = []
        content_object_ids: list[int] = []
        for page_lines in pages:
            content = ["BT", "/F1 10 Tf", f"40 {page_height} Td"]
            for line in page_lines:
                content.append(f"({_pdf_escape(line)}) Tj")
                content.append(f"0 -{line_height} Td")
            content.append("ET")
            stream = "\n".join(content).encode("latin-1", errors="replace")
            content_object_ids.append(len(objects))
            objects.append(b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream")
            page_object_ids.append(len(objects))
            objects.append(b"")
        pages_id = len(objects)
        kids = " ".join(f"{page_id} 0 R" for page_id in page_object_ids).encode("ascii")
        objects.append(b"<< /Type /Pages /Kids [" + kids + b"] /Count " + str(len(page_object_ids)).encode("ascii") + b" >>")
        font_id = len(objects)
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        catalog_id = len(objects)
        objects.append(b"<< /Type /Catalog /Pages " + str(pages_id).encode("ascii") + b" 0 R >>")
        for page_id, content_id in zip(page_object_ids, content_object_ids, strict=True):
            objects[page_id] = (
                b"<< /Type /Page /Parent "
                + str(pages_id).encode("ascii")
                + b" 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 "
                + str(font_id).encode("ascii")
                + b" 0 R >> >> /Contents "
                + str(content_id).encode("ascii")
                + b" 0 R >>"
            )
        output = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for object_id in range(1, len(objects)):
            offsets.append(len(output))
            output.extend(f"{object_id} 0 obj\n".encode("ascii"))
            output.extend(objects[object_id])
            output.extend(b"\nendobj\n")
        xref_offset = len(output)
        output.extend(f"xref\n0 {len(objects)}\n".encode("ascii"))
        output.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
        output.extend(
            b"trailer\n<< /Size "
            + str(len(objects)).encode("ascii")
            + b" /Root "
            + str(catalog_id).encode("ascii")
            + b" 0 R >>\nstartxref\n"
            + str(xref_offset).encode("ascii")
            + b"\n%%EOF\n"
        )
        output_path.write_bytes(bytes(output))

    def export_payload(self, project_id: str) -> dict[str, object]:
        report = self.build_project_report(project_id)
        return asdict(report)


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
