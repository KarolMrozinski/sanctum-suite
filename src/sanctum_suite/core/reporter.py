from pathlib import Path
from jinja2 import Template


class ComplianceReportGenerator:
    """Generator raportów audytowych dla zarządu i zespołów Security Operations Center (SOC)."""

    REPORT_TEMPLATE = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>SANCTUM-SUITE Executive Resilience Report</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 40px; }
            .card { background-color: #1e293b; border-radius: 8px; padding: 24px; margin-bottom: 20px; border: 1px solid #334155; }
            h1 { color: #38bdf8; }
            .score { font-size: 32px; font-weight: bold; color: {{ score_color }}; }
            table { width: 100%; border-collapse: collapse; margin-top: 15px; }
            th, td { text-align: left; padding: 12px; border-bottom: 1px solid #334155; }
            th { background-color: #0f172a; color: #94a3b8; }
        </style>
    </head>
    <body>
        <h1>🏛️ SANCTUM-SUITE Resilience Report</h1>
        <div class="card">
            <h2>Audit Summary: {{ audit_data.target }}</h2>
            <p>Audit ID: <strong>{{ audit_data.audit_id }}</strong></p>
            <p>Threat Score: <span class="score">{{ "%.1f"|format(audit_data.overall_score) }} / 100</span></p>
            <p>Severity Level: <strong>{{ audit_data.risk_level }}</strong></p>
        </div>

        <div class="card">
            <h3>Discovered Subdomains & Assets</h3>
            <table>
                <tr><th>Subdomain / Asset</th><th>Status</th></tr>
                {% for sub in audit_data.osint_summary.subdomains %}
                <tr><td>{{ sub }}</td><td style="color: #f43f5e;">EXPOSED</td></tr>
                {% endfor %}
            </table>
        </div>
    </body>
    </html>
    """

    def generate_html_report(self, audit_data: dict, output_filename: str = "report.html") -> str:
        score_color = "#f43f5e" if audit_data["overall_score"] > 50 else "#10b981"
        template = Template(self.REPORT_TEMPLATE)
        html_content = template.render(audit_data=audit_data, score_color=score_color)

        output_path = Path(output_filename)
        output_path.write_text(html_content, encoding="utf-8")
        return str(output_path.resolve())