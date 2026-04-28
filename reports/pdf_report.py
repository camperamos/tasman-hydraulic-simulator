from datetime import datetime
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch


TASMAN_BLUE = colors.HexColor("#008FE3")
TASMAN_ORANGE = colors.HexColor("#F28C00")
LIGHT_BLUE = colors.HexColor("#EAF5FC")
LIGHT_GREY = colors.HexColor("#F2F2F2")


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


def build_table(data, header=True, col_widths=None):
    table = Table(data, colWidths=col_widths)

    style = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]

    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), TASMAN_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]

    table.setStyle(TableStyle(style))
    return table


def generate_pdf_report(
    filename,
    job_info,
    table,
    chart,
    warning=None,
    solid_table=None,
    inputs_table=None,
):
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=30,
        bottomMargin=30,
    )

    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="TasmanTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            textColor=TASMAN_BLUE,
            alignment=1,
            spaceAfter=8,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ReportSubtitle",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.grey,
            alignment=1,
            spaceAfter=10,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=TASMAN_BLUE,
            spaceBefore=10,
            spaceAfter=6,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SmallText",
            parent=styles["Normal"],
            fontSize=8,
            textColor=colors.grey,
            alignment=1,
        )
    )

    story = []

    logo_path = os.path.join("assets", "tasman_logo.png")

    if os.path.exists(logo_path):
        story.append(Image(logo_path, width=3.6 * inch, height=1.0 * inch))
        story.append(Spacer(1, 6))

    story.append(Paragraph("Hydraulic Calculation Report", styles["TasmanTitle"]))
    story.append(
        Paragraph(
            "Tasman Oil Tools | Rentals - Services - Solutions",
            styles["ReportSubtitle"],
        )
    )

    header_data = [
        ["Well Name", job_info.get("well_name") or "-"],
        ["Target Depth (m)", job_info.get("target_depth") or "-"],
        ["Calculation", job_info.get("calculation") or "-"],
        ["Generated", datetime.now().strftime("%Y-%m-%d %H:%M")],
    ]

    header = build_table(header_data, header=False, col_widths=[160, 330])
    header.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), LIGHT_BLUE),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ]
        )
    )

    story.append(header)
    story.append(Spacer(1, 12))

    story.append(Paragraph("1. Input Parameters", styles["SectionTitle"]))

    if inputs_table is not None:
        input_data = [inputs_table.columns.tolist()] + inputs_table.values.tolist()
        story.append(build_table(input_data, header=True, col_widths=[245, 245]))
    else:
        story.append(Paragraph("No input table available.", styles["Normal"]))

    story.append(Spacer(1, 10))

    section_number = 2

    if warning:
        story.append(Paragraph(f"{section_number}. Operational Warning", styles["SectionTitle"]))
        section_number += 1

        warning_table = Table([[warning]], colWidths=[490])
        warning_table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.5, TASMAN_ORANGE),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.yellow),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )

        story.append(warning_table)
        story.append(Spacer(1, 10))

    if solid_table is not None:
        story.append(Paragraph(f"{section_number}. Solid Properties", styles["SectionTitle"]))
        section_number += 1

        solid_data = [solid_table.columns.tolist()] + solid_table.values.tolist()
        story.append(build_table(solid_data, header=True, col_widths=[245, 245]))
        story.append(Spacer(1, 10))

    story.append(Paragraph(f"{section_number}. Results Table", styles["SectionTitle"]))
    section_number += 1

    result_data = [table.columns.tolist()]

    for row in table.values:
        formatted_row = []
        for col, val in zip(table.columns, row):
            formatted_row.append(fmt(val, is_flow=("Flow" in col or "Rate" in col)))
        result_data.append(formatted_row)

    story.append(build_table(result_data, header=True))
    story.append(Spacer(1, 12))

    if chart and os.path.exists(chart):
        story.append(Paragraph(f"{section_number}. Results Chart", styles["SectionTitle"]))
        story.append(Image(chart, width=460, height=275))

    story.append(Spacer(1, 14))

    disclaimer = (
        "This report was generated using Tasman Oil Tools Hydraulic Simulator. "
        "Results are intended for engineering screening and operational support. "
        "Final operational decisions should consider field conditions, equipment limits, "
        "well geometry, and company procedures."
    )

    story.append(Paragraph(disclaimer, styles["SmallText"]))

    doc.build(story)