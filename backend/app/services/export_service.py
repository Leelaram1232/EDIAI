"""
Export Service — generates documents in PDF, Excel, and Word formats.
"""
import io
import uuid
from datetime import datetime
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ExportService:
    """Generates export documents in various formats."""

    async def generate_mapping_doc(self, data: dict, format: str = "xlsx") -> tuple[bytes, str]:
        """Generate a mapping documentation file."""
        if format == "xlsx":
            return self._mapping_to_excel(data)
        elif format == "pdf":
            return self._mapping_to_pdf(data)
        else:
            return self._mapping_to_text(data)

    def _mapping_to_excel(self, data: dict) -> tuple[bytes, str]:
        """Generate mapping doc as Excel."""
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

        wb = Workbook()
        ws = wb.active
        ws.title = "Field Mapping"

        # Styling
        header_font = Font(bold=True, color="FFFFFF", size=11)
        header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
        border = Border(
            left=Side(style='thin'), right=Side(style='thin'),
            top=Side(style='thin'), bottom=Side(style='thin')
        )

        # Headers
        headers = ["#", "Source Field", "Target Field", "Rule", "Data Type", "Description", "Notes"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')
            cell.border = border

        # Data rows
        mappings = data.get("mappings", [])
        for row_idx, mapping in enumerate(mappings, 2):
            ws.cell(row=row_idx, column=1, value=row_idx - 1).border = border
            ws.cell(row=row_idx, column=2, value=mapping.get("source", "")).border = border
            ws.cell(row=row_idx, column=3, value=mapping.get("target", "")).border = border
            ws.cell(row=row_idx, column=4, value=mapping.get("rule", "")).border = border
            ws.cell(row=row_idx, column=5, value=mapping.get("data_type", "")).border = border
            ws.cell(row=row_idx, column=6, value=mapping.get("description", "")).border = border
            ws.cell(row=row_idx, column=7, value=mapping.get("notes", "")).border = border

        # Auto-adjust column widths
        for col in ws.columns:
            max_length = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(50, max_length + 4)

        output = io.BytesIO()
        wb.save(output)
        filename = f"mapping_doc_{uuid.uuid4().hex[:8]}.xlsx"
        return output.getvalue(), filename

    def _mapping_to_pdf(self, data: dict) -> tuple[bytes, str]:
        """Generate mapping doc as PDF."""
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors

        output = io.BytesIO()
        doc = SimpleDocTemplate(output, pagesize=landscape(A4))
        elements = []
        styles = getSampleStyleSheet()

        # Title
        elements.append(Paragraph(data.get("title", "Field Mapping Document"), styles["Title"]))
        elements.append(Spacer(1, 20))

        # Table
        headers = ["#", "Source", "Target", "Rule", "Type", "Description"]
        table_data = [headers]
        for i, m in enumerate(data.get("mappings", []), 1):
            table_data.append([
                str(i), m.get("source", ""), m.get("target", ""),
                m.get("rule", ""), m.get("data_type", ""), m.get("description", "")
            ])

        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E79')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F0F4F8')]),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(table)

        doc.build(elements)
        filename = f"mapping_doc_{uuid.uuid4().hex[:8]}.pdf"
        return output.getvalue(), filename

    def _mapping_to_text(self, data: dict) -> tuple[bytes, str]:
        """Generate mapping doc as text."""
        lines = [data.get("title", "Field Mapping Document"), "=" * 60, ""]
        for i, m in enumerate(data.get("mappings", []), 1):
            lines.append(f"{i}. {m.get('source', 'N/A')} → {m.get('target', 'N/A')}")
            lines.append(f"   Rule: {m.get('rule', 'N/A')}")
            lines.append(f"   Type: {m.get('data_type', 'N/A')}")
            lines.append(f"   Desc: {m.get('description', '')}")
            lines.append("")

        content = "\n".join(lines)
        filename = f"mapping_doc_{uuid.uuid4().hex[:8]}.txt"
        return content.encode("utf-8"), filename


export_service = ExportService()
