from datetime import datetime
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet


def fmt(val, is_flow=False):
    if val is None:
        return "-"

    try:
        val = float(str(val).replace(",", ""))
    except (ValueError, TypeError):
        return str(val)

    if is_flow:
        return f"{val:.1f}"

    return f"{int(round(val)):,}"


def generate_pdf_report(filename, job_info, table, chart, warning=None, solid_table=None):
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    doc = SimpleDocTemplate(filename, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("<b>Pressure & Hydraulics Simulator</b>", styles["Title"]))
    story.append(Spacer(1, 10))

    header = Table([
        ["Well Name", job_info.get("well_name") or "-"],
        ["Target Depth (m)", job_info.get("target_depth") or "-"],
        ["Calculation", job_info.get("calculation") or "-"],
        ["Generated", datetime.now().strftime("%Y-%m-%d %H:%M")]
    ], colWidths=[160, 300])

    header.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    story.append(header)
    story.append(Spacer(1, 12))

    if warning:
        w = Table([[warning]], colWidths=[460])
        w.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.orange),
            ("BACKGROUND", (0, 0), (-1, -1), colors.yellow),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(w)
        story.append(Spacer(1, 12))

    if solid_table is not None:
        story.append(Paragraph("<b>Solid Properties</b>", styles["Heading2"]))

        solid_data = [solid_table.columns.tolist()] + solid_table.values.tolist()
        t = Table(solid_data)

        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))

        story.append(t)
        story.append(Spacer(1, 12))

    story.append(Paragraph("<b>Results Table</b>", styles["Heading2"]))

    tdata = [table.columns.tolist()]

    for row in table.values:
        r = []
        for col, val in zip(table.columns, row):
            r.append(fmt(val, is_flow=("Flow" in col or "Rate" in col)))
        tdata.append(r)

    t = Table(tdata)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    story.append(t)
    story.append(Spacer(1, 12))

    if chart and os.path.exists(chart):
        story.append(Paragraph("<b>Results Chart</b>", styles["Heading2"]))
        story.append(Image(chart, width=420, height=250))

    doc.build(story)