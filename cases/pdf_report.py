# -*- coding: utf-8 -*-
"""Génération du PDF d'un rapport d'intervention (ReportLab)."""
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

TEAL = colors.HexColor("#0f6e62")
AMBER = colors.HexColor("#e0992f")
INK = colors.HexColor("#15302b")
SOFT = colors.HexColor("#5a6b66")


def render_report_pdf(report):
    """Retourne les octets d'un PDF Amal pour un objet Report."""
    case = report.case
    s = case.student
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=20 * mm, bottomMargin=18 * mm,
                            leftMargin=20 * mm, rightMargin=20 * mm, title=report.title)
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], textColor=INK, fontSize=18, spaceAfter=2)
    sub = ParagraphStyle("sub", parent=styles["Normal"], textColor=SOFT, fontSize=9, spaceAfter=12)
    body = ParagraphStyle("body", parent=styles["Normal"], textColor=INK, fontSize=10.5, leading=16)
    foot = ParagraphStyle("foot", parent=styles["Normal"], textColor=SOFT, fontSize=8, leading=11)

    elems = []
    # En-tête bandeau
    head = Table([["Amal", report.title]], colWidths=[30 * mm, 130 * mm])
    head.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), TEAL),
        ("TEXTCOLOR", (0, 0), (0, 0), colors.white),
        ("FONTSIZE", (0, 0), (0, 0), 20), ("FONTNAME", (0, 0), (0, 0), "Times-Bold"),
        ("ALIGN", (0, 0), (0, 0), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TEXTCOLOR", (1, 0), (1, 0), INK), ("FONTSIZE", (1, 0), (1, 0), 13),
        ("FONTNAME", (1, 0), (1, 0), "Helvetica-Bold"), ("LEFTPADDING", (1, 0), (1, 0), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12), ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    elems += [head, Spacer(1, 10)]

    elems.append(Paragraph(f"Dossier {s.code}", h1))
    elems.append(Paragraph(
        f"Niveau : {s.grade_level} &nbsp;·&nbsp; Gouvernorat : {s.governorate or 'N/A'} &nbsp;·&nbsp; "
        f"Généré le {report.created_at:%d/%m/%Y à %H:%M} par {report.generated_by.username if report.generated_by else 'système'}", sub))

    # Tableau d'indicateurs
    data = [
        ["Indicateur", "Valeur"],
        ["Score de risque", f"{case.risk_score}/100 ({case.risk_band})"],
        ["Absentéisme", f"{s.absences_percentage}%"],
        ["Chute des notes", f"{s.grade_drop}/20"],
        ["Signalements disciplinaires", str(s.disciplinary_reports)],
        ["Statut du dossier", case.get_status_display()],
    ]
    tbl = Table(data, colWidths=[80 * mm, 80 * mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e7e0d4")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f3ea")]),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elems += [tbl, Spacer(1, 14)]

    # Narratif (Ollama ou repli)
    tag = "Rédigé par l'assistant IA" if report.ai_generated else "Modèle structuré"
    elems.append(Paragraph(f"Rapport d'intervention <font color='#5a6b66' size=8>({tag})</font>", h1))
    elems.append(Spacer(1, 6))
    for para in report.narrative.split("\n"):
        if para.strip():
            elems.append(Paragraph(para.replace("\n", "<br/>"), body))
            elems.append(Spacer(1, 4))

    elems.append(Spacer(1, 16))
    elems.append(Paragraph(
        "⚠ Document d'aide à la décision — la validation par un professionnel est requise. "
        "Données synthétiques, usage pédagogique. © Amal — SESAME University.", foot))

    doc.build(elems)
    buf.seek(0)
    return buf.getvalue()
