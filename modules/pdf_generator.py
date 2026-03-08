"""
PDF Generator Module
Creates a professional, branded SEO audit report PDF using ReportLab.
"""

import os
import re
import pathlib
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether, Image,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.utils import ImageReader

try:
    from zoneinfo import ZoneInfo
    _EASTERN = ZoneInfo("America/New_York")
except Exception:
    _EASTERN = None

# ── Logo path (resolved relative to this file) ───────────────────────────────
_STATIC_DIR = pathlib.Path(__file__).parent.parent / "static"
LOGO_PATH = str(_STATIC_DIR / "logo.png")
ICON_PATH = str(_STATIC_DIR / "icon-512.png")

# ── Brand Colors ─────────────────────────────────────────────────────────────
BRAND_BLUE   = colors.HexColor("#1a56db")
BRAND_NAVY   = colors.HexColor("#0a1627")
BRAND_DARK   = colors.HexColor("#1e293b")
BRAND_ACCENT = colors.HexColor("#0ea5e9")
BRAND_SUCCESS = colors.HexColor("#10b981")
BRAND_WARNING = colors.HexColor("#f59e0b")
BRAND_DANGER  = colors.HexColor("#ef4444")
BRAND_LIGHT_BG = colors.HexColor("#f8fafc")
BRAND_BORDER   = colors.HexColor("#e2e8f0")
WHITE      = colors.white
LIGHT_GRAY = colors.HexColor("#94a3b8")


def _now_et_str(fmt="%B %d, %Y"):
    if _EASTERN:
        return datetime.now(_EASTERN).strftime(fmt) + " ET"
    return datetime.now().strftime(fmt)


def _severity_color(severity):
    return {"critical": BRAND_DANGER, "high": colors.HexColor("#f97316"),
            "medium": BRAND_WARNING, "low": colors.HexColor("#6b7280")}.get(severity, BRAND_DARK)


def _impact_color(impact):
    return {"High": BRAND_DANGER, "Medium": BRAND_WARNING, "Low": BRAND_SUCCESS}.get(impact, BRAND_DARK)


def _score_color(score):
    if score >= 80: return BRAND_SUCCESS
    elif score >= 60: return BRAND_WARNING
    return BRAND_DANGER


def _clean(text):
    """Strip any JSON/markdown artifacts that might leak into text fields."""
    if not text:
        return ""
    text = str(text).strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    if text.startswith('{') or text.startswith('['):
        m = re.search(r'"(?:summary|text)"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', text)
        if m:
            return m.group(1).replace('\\"', '"')
        return ""
    return text


class PDFGenerator:
    def create_report(self, audit_id, business_name, url, city, category,
                      site_data, competitor_data, ai_report):
        os.makedirs("/tmp/ar_reports", exist_ok=True)
        path = os.path.join("/tmp/ar_reports", f"{audit_id}.pdf")

        doc = SimpleDocTemplate(
            path, pagesize=letter,
            leftMargin=0.75 * inch, rightMargin=0.75 * inch,
            topMargin=0.6 * inch, bottomMargin=0.6 * inch,
        )

        styles = self._build_styles()
        story = []

        # Cover
        story += self._cover(business_name, url, city, category, site_data, styles)
        story.append(PageBreak())

        # Executive Summary
        story += self._executive_summary(site_data, ai_report, styles)
        story.append(Spacer(1, 0.2 * inch))

        # SEO Checklist
        story += self._score_breakdown(site_data, styles)
        story.append(Spacer(1, 0.2 * inch))

        # Issues Found
        story += self._issues_section(site_data, styles)
        story.append(PageBreak())

        # Action Plan
        story += self._todo_section(ai_report, styles)
        story.append(Spacer(1, 0.2 * inch))

        # Quick Wins
        story += self._quick_wins_section(ai_report, styles)
        story.append(Spacer(1, 0.2 * inch))

        # Keywords
        story += self._keywords_section(ai_report, styles)
        story.append(PageBreak())

        # Google Business Profile
        story += self._google_business_section(ai_report, styles)
        story.append(Spacer(1, 0.2 * inch))

        # Local Citations
        story += self._local_citations_section(ai_report, styles)
        story.append(Spacer(1, 0.2 * inch))

        # Content Recommendations
        story += self._content_section(ai_report, styles)
        story.append(PageBreak())

        # Competitor Analysis
        if competitor_data:
            story += self._competitor_section(site_data, competitor_data, ai_report, styles)
            story.append(Spacer(1, 0.2 * inch))

        # Strengths
        story += self._wins_section(site_data, styles)
        story.append(Spacer(1, 0.3 * inch))

        # Footer CTA
        story += self._footer_cta(ai_report, styles)

        doc.build(story, onFirstPage=self._page_header_footer,
                  onLaterPages=self._page_header_footer)
        return path

    # ── Styles ────────────────────────────────────────────────────────────────
    def _build_styles(self):
        base = getSampleStyleSheet()
        return {
            "h1": ParagraphStyle("h1", parent=base["Normal"], fontSize=22,
                                  textColor=WHITE, fontName="Helvetica-Bold",
                                  spaceAfter=4, alignment=TA_CENTER),
            "h2": ParagraphStyle("h2", parent=base["Normal"], fontSize=16,
                                  textColor=BRAND_DARK, fontName="Helvetica-Bold",
                                  spaceAfter=6, spaceBefore=4),
            "h3": ParagraphStyle("h3", parent=base["Normal"], fontSize=12,
                                  textColor=BRAND_BLUE, fontName="Helvetica-Bold",
                                  spaceAfter=5),
            "body": ParagraphStyle("body", parent=base["Normal"], fontSize=10,
                                    textColor=BRAND_DARK, fontName="Helvetica",
                                    spaceAfter=5, leading=14),
            "small": ParagraphStyle("small", parent=base["Normal"], fontSize=8,
                                     textColor=LIGHT_GRAY, fontName="Helvetica", spaceAfter=3),
            "caption": ParagraphStyle("caption", parent=base["Normal"], fontSize=9,
                                       textColor=BRAND_DARK, fontName="Helvetica", spaceAfter=3),
            "center": ParagraphStyle("center", parent=base["Normal"], fontSize=10,
                                      fontName="Helvetica", textColor=BRAND_DARK,
                                      alignment=TA_CENTER),
            "bullet": ParagraphStyle("bullet", parent=base["Normal"], fontSize=10,
                                      textColor=BRAND_DARK, fontName="Helvetica",
                                      leftIndent=12, spaceAfter=4, leading=14,
                                      bulletIndent=0, firstLineIndent=-12),
            "tag": ParagraphStyle("tag", parent=base["Normal"], fontSize=8,
                                   textColor=WHITE, fontName="Helvetica-Bold",
                                   alignment=TA_CENTER),
        }

    # ── Cover ─────────────────────────────────────────────────────────────────
    def _cover(self, business_name, url, city, category, site_data, styles):
        score = site_data.get("overall_score", 0)
        grade = _score_to_grade(score)
        score_col = _score_color(score)
        date_str = _now_et_str()

        elements = [Spacer(1, 0.2 * inch)]

        # ── Dark navy header band with logo + title ───────────────────────────
        logo_cell = ""
        if os.path.exists(LOGO_PATH):
            try:
                logo_img = Image(LOGO_PATH, width=2.0 * inch, height=0.5 * inch)
                logo_cell = logo_img
            except Exception:
                logo_cell = Paragraph("<b>ATLAS REYNOLDS</b>",
                                      ParagraphStyle("lf", fontSize=13, textColor=WHITE,
                                                     fontName="Helvetica-Bold"))

        title_para = Paragraph("LOCAL SEO AUDIT REPORT",
                               ParagraphStyle("ct", fontSize=18, textColor=WHITE,
                                              fontName="Helvetica-Bold", alignment=TA_RIGHT))

        header_data = [[logo_cell, title_para]]
        header_table = Table(header_data, colWidths=[3.5 * inch, 3.5 * inch],
                             style=TableStyle([
                                 ("BACKGROUND", (0, 0), (-1, -1), BRAND_NAVY),
                                 ("TOPPADDING", (0, 0), (-1, -1), 14),
                                 ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
                                 ("LEFTPADDING", (0, 0), (-1, -1), 16),
                                 ("RIGHTPADDING", (0, 0), (-1, -1), 16),
                                 ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                 ("LINEBELOW", (0, 0), (-1, -1), 3, BRAND_BLUE),
                             ]))
        elements.append(header_table)

        # ── Business info card ────────────────────────────────────────────────
        biz_style = ParagraphStyle("biz", fontSize=20, textColor=BRAND_DARK,
                                   fontName="Helvetica-Bold", alignment=TA_CENTER)
        url_style = ParagraphStyle("url", fontSize=10, textColor=BRAND_BLUE,
                                   fontName="Helvetica", alignment=TA_CENTER)
        loc_style = ParagraphStyle("loc", fontSize=11, textColor=LIGHT_GRAY,
                                   fontName="Helvetica", alignment=TA_CENTER)

        info_data = [
            [Paragraph(f"<b>{business_name}</b>", biz_style)],
            [Paragraph(url, url_style)],
            [Paragraph(f"{category}  ·  {city}", loc_style)],
            [Spacer(1, 0.1 * inch)],
        ]
        info_table = Table(info_data, colWidths=[7 * inch],
                           style=TableStyle([
                               ("BACKGROUND", (0, 0), (-1, -1), BRAND_LIGHT_BG),
                               ("TOPPADDING", (0, 0), (-1, -1), 8),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                               ("LEFTPADDING", (0, 0), (-1, -1), 20),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 20),
                           ]))
        elements.append(info_table)

        # ── Score / Grade / Stats row ─────────────────────────────────────────
        issues_count = len(site_data.get("issues", []))
        wins_count   = len(site_data.get("wins", []))

        num_style   = ParagraphStyle("sc", fontSize=52, fontName="Helvetica-Bold",
                                     textColor=score_col, alignment=TA_CENTER,
                                     leading=56, spaceAfter=0)
        grade_style = ParagraphStyle("gr", fontSize=30, fontName="Helvetica-Bold",
                                     textColor=score_col, alignment=TA_CENTER,
                                     leading=34, spaceAfter=0)
        lbl_style   = ParagraphStyle("lb", fontSize=10, fontName="Helvetica",
                                     textColor=LIGHT_GRAY, alignment=TA_CENTER)

        score_inner = Table(
            [[Paragraph(f"{score}", num_style)],
             [Paragraph(grade, grade_style)],
             [Paragraph("SEO Score / Grade", lbl_style)]],
            rowHeights=[0.75 * inch, 0.5 * inch, 0.25 * inch],
            style=TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ])
        )

        issues_inner = Table(
            [[Paragraph(f"{issues_count}", ParagraphStyle("ic", fontSize=36,
                        fontName="Helvetica-Bold", textColor=BRAND_DANGER,
                        alignment=TA_CENTER))],
             [Paragraph("Issues Found", lbl_style)]],
            rowHeights=[0.6 * inch, 0.25 * inch],
            style=TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"),
                               ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                               ("TOPPADDING", (0, 0), (-1, -1), 4),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 4)])
        )

        wins_inner = Table(
            [[Paragraph(f"{wins_count}", ParagraphStyle("wc", fontSize=36,
                        fontName="Helvetica-Bold", textColor=BRAND_SUCCESS,
                        alignment=TA_CENTER))],
             [Paragraph("Strengths Found", lbl_style)]],
            rowHeights=[0.6 * inch, 0.25 * inch],
            style=TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"),
                               ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                               ("TOPPADDING", (0, 0), (-1, -1), 4),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 4)])
        )

        score_table = Table(
            [[issues_inner, score_inner, wins_inner]],
            colWidths=[2.1 * inch, 2.8 * inch, 2.1 * inch],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), BRAND_LIGHT_BG),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("LINEBELOW", (0, 0), (-1, 0), 3, BRAND_BLUE),
                ("LINEBETWEEN", (0, 0), (2, 0), 1, BRAND_BORDER),
            ])
        )
        elements.append(score_table)
        elements.append(Spacer(1, 0.12 * inch))

        elements.append(Paragraph(
            f"Prepared: {date_str}  ·  Confidential — For Business Owner Use Only",
            ParagraphStyle("dt", fontSize=8, textColor=LIGHT_GRAY,
                           alignment=TA_CENTER, fontName="Helvetica")
        ))
        return elements

    # ── Executive Summary ─────────────────────────────────────────────────────
    def _executive_summary(self, site_data, ai_report, styles):
        elements = [
            Paragraph("Executive Summary", styles["h2"]),
            HRFlowable(width="100%", thickness=2, color=BRAND_BLUE, spaceAfter=10),
        ]

        summary = _clean(ai_report.get("summary", ""))
        score_interp = _clean(ai_report.get("score_interpretation", ""))

        if not summary:
            summary = _score_to_text(site_data.get("overall_score", 0))

        elements.append(Paragraph(summary, styles["body"]))
        if score_interp:
            elements.append(Paragraph(f"<i>{score_interp}</i>", styles["body"]))

        critical = ai_report.get("critical_findings", [])
        if critical:
            elements.append(Spacer(1, 0.08 * inch))
            elements.append(Paragraph("Critical Findings", styles["h3"]))
            for finding in critical[:4]:
                elements.append(Paragraph(f"• {_clean(finding)}", styles["bullet"]))

        return elements

    # ── SEO Checklist ─────────────────────────────────────────────────────────
    def _score_breakdown(self, site_data, styles):
        raw = site_data.get("raw", {})
        categories = [
            ("Technical Foundation", [
                ("HTTPS / SSL", raw.get("https", False)),
                ("Mobile-Friendly (Viewport)", raw.get("has_viewport", False)),
                ("Page Speed < 2s", raw.get("load_time_ms", 9999) < 2000),
            ]),
            ("On-Page SEO", [
                ("Title Tag Present", bool(raw.get("title"))),
                ("Title Length 50–65 chars", 50 <= raw.get("title_length", 0) <= 65),
                ("Meta Description Present", bool(raw.get("meta_description"))),
                ("H1 Tag (exactly one)", raw.get("h1_count", 0) == 1),
                ("H2 Subheadings", raw.get("h2_count", 0) > 0),
                ("Image Alt Text", raw.get("images_missing_alt", 1) == 0),
            ]),
            ("Local SEO Signals", [
                ("Phone Number on Page", len(raw.get("phone_numbers", [])) > 0),
                ("Address on Page", raw.get("has_address_on_page", False)),
                ("Google Maps Embed", raw.get("has_map_embed", False)),
                ("LocalBusiness Schema", raw.get("has_local_schema", False)),
                ("Reviews / Testimonials", raw.get("has_reviews_mention", False)),
                ("Contact Page Link", raw.get("has_contact_link", False)),
            ]),
            ("Content Quality", [
                ("300+ Words of Content", raw.get("word_count", 0) >= 300),
                ("Internal Links (3+)", raw.get("internal_link_count", 0) >= 3),
                ("Open Graph Tags", raw.get("has_og_title", False) and raw.get("has_og_image", False)),
                ("Favicon", raw.get("has_favicon", False)),
            ]),
        ]

        elements = [
            Paragraph("SEO Checklist", styles["h2"]),
            HRFlowable(width="100%", thickness=2, color=BRAND_BLUE, spaceAfter=10),
        ]

        for cat_name, checks in categories:
            passed = sum(1 for _, v in checks if v)
            total = len(checks)
            hdr = ParagraphStyle("ch", fontSize=11, fontName="Helvetica-Bold", textColor=BRAND_DARK)
            rows = [[
                Paragraph(cat_name, hdr),
                Paragraph(f"{passed}/{total} passed",
                          ParagraphStyle("cp", fontSize=10, fontName="Helvetica",
                                         textColor=BRAND_SUCCESS if passed == total else BRAND_WARNING,
                                         alignment=TA_RIGHT))
            ]]
            for label, passing in checks:
                icon = "✓" if passing else "✗"
                rows.append([
                    Paragraph(f"  {label}", styles["caption"]),
                    Paragraph(icon, ParagraphStyle("ic2", fontSize=11, fontName="Helvetica-Bold",
                                                    textColor=BRAND_SUCCESS if passing else BRAND_DANGER,
                                                    alignment=TA_RIGHT))
                ])
            t = Table(rows, colWidths=[5.8 * inch, 1.2 * inch],
                      style=TableStyle([
                          ("BACKGROUND", (0, 0), (-1, 0), BRAND_LIGHT_BG),
                          ("TOPPADDING", (0, 0), (-1, -1), 5),
                          ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                          ("LEFTPADDING", (0, 0), (-1, -1), 8),
                          ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                          ("LINEBELOW", (0, 0), (-1, 0), 1, BRAND_BORDER),
                          ("LINEBELOW", (0, -1), (-1, -1), 1, BRAND_BORDER),
                          ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, BRAND_LIGHT_BG]),
                      ]))
            elements.append(t)
            elements.append(Spacer(1, 0.1 * inch))

        return elements

    # ── Issues Found ──────────────────────────────────────────────────────────
    def _issues_section(self, site_data, styles):
        issues = site_data.get("issues", [])
        if not issues:
            return []

        elements = [
            Paragraph("Issues Found", styles["h2"]),
            HRFlowable(width="100%", thickness=2, color=BRAND_DANGER, spaceAfter=10),
        ]

        severity_order = ["critical", "high", "medium", "low"]
        grouped = {s: [] for s in severity_order}
        for issue in issues:
            grouped.setdefault(issue.get("severity", "low"), []).append(issue)

        for sev in severity_order:
            sev_issues = grouped.get(sev, [])
            if not sev_issues:
                continue
            col = _severity_color(sev)
            sev_header = Table(
                [[Paragraph(f"  {sev.upper()} PRIORITY",
                            ParagraphStyle("sl", fontSize=10, fontName="Helvetica-Bold",
                                           textColor=WHITE))]],
                colWidths=[7 * inch],
                style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), col),
                                   ("TOPPADDING", (0, 0), (-1, -1), 5),
                                   ("BOTTOMPADDING", (0, 0), (-1, -1), 5)])
            )
            elements.append(sev_header)
            for issue in sev_issues:
                row_table = Table(
                    [[Paragraph(f"• {issue['text']}", styles["body"])]],
                    colWidths=[7 * inch],
                    style=TableStyle([
                        ("LEFTPADDING", (0, 0), (-1, -1), 12),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ("LINEBELOW", (0, 0), (-1, -1), 0.5, BRAND_BORDER),
                    ])
                )
                elements.append(row_table)
            elements.append(Spacer(1, 0.06 * inch))

        return elements

    # ── Action Plan ───────────────────────────────────────────────────────────
    def _todo_section(self, ai_report, styles):
        todos = ai_report.get("todo_list", [])
        if not todos:
            return []

        elements = [
            Paragraph("Your Action Plan", styles["h2"]),
            HRFlowable(width="100%", thickness=2, color=BRAND_BLUE, spaceAfter=10),
            Paragraph("Complete these tasks in order of priority. Each fix will improve your Google ranking.",
                      styles["body"]),
            Spacer(1, 0.08 * inch),
        ]

        for item in todos:
            priority = item.get("priority", "?")
            category = _clean(item.get("category", ""))
            task     = _clean(item.get("task", ""))
            how_to   = _clean(item.get("how_to", ""))
            impact   = _clean(item.get("impact", "Medium"))
            time_est = _clean(item.get("time_estimate", ""))
            expected = _clean(item.get("expected_result", ""))

            impact_col = _impact_color(impact)

            badge = Table(
                [[Paragraph(f"#{priority}", ParagraphStyle("pr", fontSize=11,
                                                            fontName="Helvetica-Bold",
                                                            textColor=WHITE, alignment=TA_CENTER))]],
                colWidths=[0.35 * inch],
                style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), BRAND_BLUE),
                                   ("TOPPADDING", (0, 0), (-1, -1), 6),
                                   ("BOTTOMPADDING", (0, 0), (-1, -1), 6)])
            )
            imp_badge = Table(
                [[Paragraph(impact, ParagraphStyle("imp", fontSize=8, fontName="Helvetica-Bold",
                                                    textColor=WHITE, alignment=TA_CENTER))]],
                colWidths=[0.7 * inch],
                style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), impact_col),
                                   ("TOPPADDING", (0, 0), (-1, -1), 4),
                                   ("BOTTOMPADDING", (0, 0), (-1, -1), 4)])
            )

            header_table = Table(
                [[badge, Paragraph(f"<b>{task}</b>",
                                   ParagraphStyle("tsk", fontSize=11, fontName="Helvetica-Bold",
                                                  textColor=BRAND_DARK)), imp_badge]],
                colWidths=[0.45 * inch, 5.8 * inch, 0.75 * inch],
                style=TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BACKGROUND", (0, 0), (-1, -1), BRAND_LIGHT_BG),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ])
            )

            detail_rows = []
            if category:
                detail_rows.append([Paragraph(f"<b>Category:</b> {category}", styles["caption"]), ""])
            if time_est:
                detail_rows.append([Paragraph(f"<b>Time needed:</b> {time_est}", styles["caption"]), ""])
            if how_to:
                detail_rows.append([Paragraph(f"<b>How to fix:</b> {how_to}", styles["body"]), ""])
            if expected:
                detail_rows.append([Paragraph(f"<b>Expected result:</b> {expected}", styles["caption"]), ""])

            block = [header_table]
            if detail_rows:
                dt = Table(detail_rows, colWidths=[7 * inch, 0],
                           style=TableStyle([
                               ("LEFTPADDING", (0, 0), (-1, -1), 12),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                               ("TOPPADDING", (0, 0), (-1, -1), 3),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                               ("LINEBELOW", (0, -1), (-1, -1), 1, BRAND_BORDER),
                           ]))
                block.append(dt)
            block.append(Spacer(1, 0.08 * inch))
            elements.append(KeepTogether(block))

        return elements

    # ── Quick Wins ────────────────────────────────────────────────────────────
    def _quick_wins_section(self, ai_report, styles):
        wins = ai_report.get("quick_wins", [])
        if not wins:
            return []

        elements = [
            Paragraph("Quick Wins (Under 30 Minutes)", styles["h2"]),
            HRFlowable(width="100%", thickness=2, color=BRAND_SUCCESS, spaceAfter=10),
        ]
        rows = [[Paragraph(f"✓  {_clean(w)}", styles["body"])] for w in wins]
        t = Table(rows, colWidths=[7 * inch],
                  style=TableStyle([
                      ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0fdf4")),
                      ("LEFTPADDING", (0, 0), (-1, -1), 12),
                      ("TOPPADDING", (0, 0), (-1, -1), 6),
                      ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                      ("LINEBELOW", (0, 0), (-1, -2), 0.5, BRAND_BORDER),
                      ("LINEBEFORE", (0, 0), (0, -1), 3, BRAND_SUCCESS),
                  ]))
        elements.append(t)
        return elements

    # ── Keywords ─────────────────────────────────────────────────────────────
    def _keywords_section(self, ai_report, styles):
        keywords = [_clean(k) for k in ai_report.get("keyword_recommendations", []) if k]
        if not keywords:
            return []

        elements = [
            Spacer(1, 0.1 * inch),
            Paragraph("Keyword Recommendations", styles["h2"]),
            HRFlowable(width="100%", thickness=2, color=BRAND_ACCENT, spaceAfter=10),
            Paragraph("Use these keyword phrases in your title tag, meta description, H1, and page content:",
                      styles["body"]),
            Spacer(1, 0.05 * inch),
        ]
        cells = []
        for i in range(0, len(keywords), 2):
            row = [Paragraph(f"→  {keywords[i]}", styles["body"]),
                   Paragraph(f"→  {keywords[i+1]}", styles["body"]) if i + 1 < len(keywords) else Paragraph("", styles["body"])]
            cells.append(row)
        if cells:
            t = Table(cells, colWidths=[3.5 * inch, 3.5 * inch],
                      style=TableStyle([
                          ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
                          ("TOPPADDING", (0, 0), (-1, -1), 5),
                          ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                          ("LEFTPADDING", (0, 0), (-1, -1), 10),
                          ("LINEBELOW", (0, 0), (-1, -2), 0.5, BRAND_BORDER),
                      ]))
            elements.append(t)
        return elements

    # ── Google Business Profile ───────────────────────────────────────────────
    def _google_business_section(self, ai_report, styles):
        tips = [_clean(t) for t in ai_report.get("google_business_tips", []) if t]
        if not tips:
            return []

        elements = [
            Paragraph("Google Business Profile Optimization", styles["h2"]),
            HRFlowable(width="100%", thickness=2, color=BRAND_BLUE, spaceAfter=8),
            Paragraph(
                "Your Google Business Profile is often more visible than your website in local search. "
                "These improvements can directly increase calls and foot traffic.",
                styles["body"]
            ),
            Spacer(1, 0.08 * inch),
        ]

        rows = [[Paragraph(f"★  {tip}", styles["body"])] for tip in tips]
        t = Table(rows, colWidths=[7 * inch],
                  style=TableStyle([
                      ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
                      ("LEFTPADDING", (0, 0), (-1, -1), 12),
                      ("TOPPADDING", (0, 0), (-1, -1), 6),
                      ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                      ("LINEBELOW", (0, 0), (-1, -2), 0.5, BRAND_BORDER),
                      ("LINEBEFORE", (0, 0), (0, -1), 3, BRAND_BLUE),
                  ]))
        elements.append(t)
        return elements

    # ── Local Citations ───────────────────────────────────────────────────────
    def _local_citations_section(self, ai_report, styles):
        citations = [_clean(c) for c in ai_report.get("local_citations", []) if c]
        if not citations:
            return []

        elements = [
            Paragraph("Local Citation Building", styles["h2"]),
            HRFlowable(width="100%", thickness=2, color=BRAND_ACCENT, spaceAfter=8),
            Paragraph(
                "Citations (listings on other sites) strengthen your local search ranking. "
                "Consistent Name, Address, and Phone (NAP) across all platforms is critical.",
                styles["body"]
            ),
            Spacer(1, 0.08 * inch),
        ]

        rows = [[Paragraph(f"•  {cite}", styles["body"])] for cite in citations]
        t = Table(rows, colWidths=[7 * inch],
                  style=TableStyle([
                      ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0fdfa")),
                      ("LEFTPADDING", (0, 0), (-1, -1), 12),
                      ("TOPPADDING", (0, 0), (-1, -1), 6),
                      ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                      ("LINEBELOW", (0, 0), (-1, -2), 0.5, BRAND_BORDER),
                      ("LINEBEFORE", (0, 0), (0, -1), 3, BRAND_ACCENT),
                  ]))
        elements.append(t)
        return elements

    # ── Content Recommendations ───────────────────────────────────────────────
    def _content_section(self, ai_report, styles):
        recs = [_clean(r) for r in ai_report.get("content_recommendations", []) if r]
        if not recs:
            return []

        elements = [
            Paragraph("Content Strategy Recommendations", styles["h2"]),
            HRFlowable(width="100%", thickness=2, color=BRAND_WARNING, spaceAfter=8),
            Paragraph(
                "Adding the right content to your website signals to Google that you are the "
                "authoritative local business in your category.",
                styles["body"]
            ),
            Spacer(1, 0.08 * inch),
        ]

        rows = [[Paragraph(f"→  {rec}", styles["body"])] for rec in recs]
        t = Table(rows, colWidths=[7 * inch],
                  style=TableStyle([
                      ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fffbeb")),
                      ("LEFTPADDING", (0, 0), (-1, -1), 12),
                      ("TOPPADDING", (0, 0), (-1, -1), 6),
                      ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                      ("LINEBELOW", (0, 0), (-1, -2), 0.5, BRAND_BORDER),
                      ("LINEBEFORE", (0, 0), (0, -1), 3, BRAND_WARNING),
                  ]))
        elements.append(t)
        return elements

    # ── Competitor Analysis ───────────────────────────────────────────────────
    def _competitor_section(self, site_data, competitor_data, ai_report, styles):
        elements = [
            Paragraph("Competitor Analysis", styles["h2"]),
            HRFlowable(width="100%", thickness=2, color=BRAND_DARK, spaceAfter=10),
        ]

        def yn(val):
            return "✓" if val else "✗"

        your_raw = site_data.get("raw", {})
        header = [Paragraph("<b>Signal</b>", styles["caption"]),
                  Paragraph("<b>Your Site</b>", styles["caption"])]
        for i, comp in enumerate(competitor_data[:3], 1):
            header.append(Paragraph(f"<b>Comp. {i}</b>", styles["caption"]))

        signals_to_compare = [
            ("SEO Score",    str(site_data.get("overall_score", 0)),
             [str(c.get("overall_score", 0)) for c in competitor_data[:3]]),
            ("HTTPS",        yn(your_raw.get("https")),
             [yn(c.get("raw", {}).get("https")) for c in competitor_data[:3]]),
            ("Schema Markup", yn(your_raw.get("has_local_schema")),
             [yn(c.get("raw", {}).get("has_local_schema")) for c in competitor_data[:3]]),
            ("Phone on Page", yn(your_raw.get("phone_numbers")),
             [yn(c.get("raw", {}).get("phone_numbers")) for c in competitor_data[:3]]),
            ("Map Embed",    yn(your_raw.get("has_map_embed")),
             [yn(c.get("raw", {}).get("has_map_embed")) for c in competitor_data[:3]]),
            ("Reviews",      yn(your_raw.get("has_reviews_mention")),
             [yn(c.get("raw", {}).get("has_reviews_mention")) for c in competitor_data[:3]]),
            ("Word Count",   str(your_raw.get("word_count", 0)),
             [str(c.get("raw", {}).get("word_count", 0)) for c in competitor_data[:3]]),
        ]

        table_data = [header]
        for sig_name, your_val, comp_vals in signals_to_compare:
            row = [Paragraph(sig_name, styles["caption"]),
                   Paragraph(your_val, styles["caption"])]
            for cv in comp_vals:
                row.append(Paragraph(cv, styles["caption"]))
            table_data.append(row)

        n_cols = 2 + min(len(competitor_data), 3)
        col_w = 7.0 / n_cols
        t = Table(table_data, colWidths=[col_w * inch] * n_cols,
                  style=TableStyle([
                      ("BACKGROUND", (0, 0), (-1, 0), BRAND_DARK),
                      ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                      ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, BRAND_LIGHT_BG]),
                      ("TOPPADDING", (0, 0), (-1, -1), 6),
                      ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                      ("LEFTPADDING", (0, 0), (-1, -1), 6),
                      ("GRID", (0, 0), (-1, -1), 0.5, BRAND_BORDER),
                  ]))
        elements.append(t)

        gaps = [_clean(g) for g in ai_report.get("competitor_gaps", []) if g]
        if gaps:
            elements.append(Spacer(1, 0.12 * inch))
            elements.append(Paragraph("Competitive Gaps to Close", styles["h3"]))
            for gap in gaps:
                elements.append(Paragraph(f"• {gap}", styles["bullet"]))

        return elements

    # ── Strengths ─────────────────────────────────────────────────────────────
    def _wins_section(self, site_data, styles):
        wins = site_data.get("wins", [])
        if not wins:
            return []
        elements = [
            Paragraph("What You're Already Doing Right", styles["h2"]),
            HRFlowable(width="100%", thickness=2, color=BRAND_SUCCESS, spaceAfter=10),
        ]
        for win in wins:
            elements.append(Paragraph(f"✓  {win}", styles["bullet"]))
        return elements

    # ── Footer CTA ────────────────────────────────────────────────────────────
    def _footer_cta(self, ai_report, styles):
        close = _clean(ai_report.get("motivational_close", ""))
        elements = [HRFlowable(width="100%", thickness=1, color=BRAND_BORDER, spaceAfter=10)]

        if close:
            elements.append(Paragraph(close, ParagraphStyle(
                "cta", fontSize=12, fontName="Helvetica-Bold",
                textColor=BRAND_BLUE, alignment=TA_CENTER, leading=18
            )))
            elements.append(Spacer(1, 0.08 * inch))

        elements.append(Paragraph(
            "Report generated by Atlas Reynolds · atlasreynolds.com  |  "
            "Re-audit in 30 days to measure your progress.",
            ParagraphStyle("disc", fontSize=8, textColor=LIGHT_GRAY,
                           alignment=TA_CENTER, fontName="Helvetica")
        ))
        return elements

    # ── Page Header / Footer ──────────────────────────────────────────────────
    def _page_header_footer(self, canvas, doc):
        canvas.saveState()

        # ── Top bar (navy) ───────────────────────────────────────────────────
        bar_h = 0.38 * inch
        canvas.setFillColor(BRAND_NAVY)
        canvas.rect(0, letter[1] - bar_h, letter[0], bar_h, fill=1, stroke=0)

        # Logo in header bar
        if os.path.exists(LOGO_PATH):
            try:
                logo_reader = ImageReader(LOGO_PATH)
                canvas.drawImage(logo_reader,
                                  0.75 * inch, letter[1] - bar_h + 0.05 * inch,
                                  width=1.6 * inch, height=0.28 * inch,
                                  preserveAspectRatio=True, mask="auto")
            except Exception:
                canvas.setFillColor(WHITE)
                canvas.setFont("Helvetica-Bold", 9)
                canvas.drawString(0.75 * inch, letter[1] - 0.24 * inch, "ATLAS REYNOLDS")

        canvas.setFillColor(WHITE)
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(letter[0] - 0.75 * inch,
                               letter[1] - 0.24 * inch,
                               _now_et_str())

        # ── Bottom bar ───────────────────────────────────────────────────────
        canvas.setFillColor(BRAND_LIGHT_BG)
        canvas.rect(0, 0, letter[0], 0.32 * inch, fill=1, stroke=0)
        canvas.setFillColor(LIGHT_GRAY)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(0.75 * inch, 0.11 * inch,
                          "Confidential — For Business Owner Use Only · atlasreynolds.com")
        canvas.drawRightString(letter[0] - 0.75 * inch, 0.11 * inch,
                               f"Page {doc.page}")

        canvas.restoreState()


def _score_to_grade(score):
    if score >= 90: return "A"
    elif score >= 80: return "B"
    elif score >= 70: return "C"
    elif score >= 60: return "D"
    return "F"


def _score_to_text(score):
    if score >= 80:
        return "Your site is performing well above average for local SEO."
    elif score >= 60:
        return "Your site has a solid foundation but several gaps are holding you back from top rankings."
    elif score >= 40:
        return "Your site has significant SEO issues that are likely costing you customers every day."
    return "Your site has critical SEO problems. Fixing these could dramatically increase your visibility in local search."
