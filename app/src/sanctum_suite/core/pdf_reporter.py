from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


class PDFReportGenerator:
    """Generator profesjonalnych raportów audytowych PDF dla kadry zarządzającej i zespołów SOC."""

    def generate_pdf_report(self, audit_data: dict, output_filename: str = "report.pdf") -> str:
        output_path = Path(output_filename)
        doc = SimpleDocTemplate(str(output_path), pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        title_style = ParagraphStyle(
            "TitleStyle",
            parent=styles["Heading1"],
            fontSize=22,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=12,
        )

        # Nagłówek
        story.append(Paragraph("🏛️ SANCTUM-SUITE Executive Cyber Resilience Report", title_style))
        story.append(Paragraph(f"<b>Target Domain:</b> {audit_data['target']}", styles["Normal"]))
        story.append(Paragraph(f"<b>Audit ID:</b> {audit_data['audit_id']}", styles["Normal"]))
        story.append(Paragraph(f"<b>Threat Score:</b> {audit_data['overall_score']:.1f} / 100", styles["Normal"]))
        story.append(Paragraph(f"<b>Risk Level:</b> {audit_data['risk_level']}", styles["Normal"]))
        story.append(Spacer(1, 18))

        # Tabela Wykrytych Zasobów i Podatności
        table_data = [["Asset / Endpoint", "Module", "Risk Impact"]]
        for ep in audit_data.get("probed_endpoints", []):
            table_data.append([ep["url"], "SPECTRE-OSINT", "EXPOSED" if ep["is_alive"] else "OFFLINE"])

        for vuln in audit_data.get("shadow_summary", {}).get("vulnerabilities", []):
            table_data.append([vuln["endpoint"], "SHADOW-AGENT", f"CRITICAL ({vuln['issue']})"])

        report_table = Table(table_data, colWidths=[240, 140, 140])
        report_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ])
        )

        story.append(report_table)
        doc.build(story)
        return str(output_path.resolve())