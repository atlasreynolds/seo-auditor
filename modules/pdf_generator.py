"""
PDF Generator Module
Creates a professional, branded SEO audit report PDF using ReportLab.
"""

import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


# ── Brand Colors ─────────────────────────────────────────────────────────────
BRAND_BLUE = colors.HexColor("#1a56db")
BRAND_DARK = colors.HexColor("#1e293b")
BRAND_ACCENT = colors.HexColor("#0ea5e9")
BRAND_SUCCESS = colors.HexColor("#10b981")
BRAND_WARNING = colors.HexColor("#f59e0b")
BRAND_DANGER = colors.HexColor("#ef4444")
BRAND_LIGHT_BG = colors.HexColor("#f8fafc")
BRAND_BORDER = colors.HexColor("#e2e8f0")
WHITE = colors.white
LIGHT_GRAY = colors.HexColor("#94a3b8")


def _severity_color(severity: str) -> object:
    return {
        "critical": BRAND_DANGER,
        "high": colors.HexColor("#f97316"),
        "medium": BRAND_WARNING,
        "low": colors.HexColor("#6b7280"),
    }.get(severity, BRAND_DARK)


def _impact_color(impact: str) -> object:
    return {
        "High": BRAND_DANGER,
        "Medium": BRAND_WARNING,
        "Low": BRAND_SUCCESS,
    }.get(impact, BRAND_DARK)


def _score_color(score: int) -> object:
    if score >= 80:
        return BRAND_SUCCESS
    elif score >= 60:
        return BRAND_WARNING
    else:
        return BRAND_DANGER


class PDFGenerator:
    def create_report(
        self,
        audit_id: str,
        business_name: str,
        url: str,
        city: str,
        category: str,
        site_data: dict,
        competitor_data: list,
        ai_report: dict,
    ) -> str:
        os.makedirs("reports", exist_ok=True)
        path = os.path.join("reports", f"{audit_id}.pdf")

        doc = SimpleDocTemplate(
            path,
            pagesize=letter,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        styles = self._build_styles()
        story = []

        # ── Cover Section ─────────────────────────────────────────────────────
        story += self._cover(business_name, url, city, category, site_data, styles)
        story.append(PageBreak())

        # ── Executive Summary ─────────────────────────────────────────────────
        story += self._executive_summary(site_data, ai_report, styles)
        story.append(Spacer(1, 0.2 * inch))

        # ── Score Breakdown ───────────────────────────────────────────────────
        story += self._score_breakdown(site_data, styles)
        story.append(Spacer(1, 0.2 * inch))

        # ── Issues Found ──────────────────────────────────────────────────────
        story += self._issues_section(site_data, styles)
        story.append(PageBreak())

        # ── Prioritized To-Do List ────────────────────────────────────────────
        story += self._todo_section(ai_report, styles)
        story.append(Spacer(1, 0.2 * inch))

        # ── Quick Wins ────────────────────────────────────────────────────────
        story += self._quick_wins_section(ai_report, styles)
        story.append(Spacer(1, 0.2 * inch))

        # ── Keyword Recommendations ───────────────────────────────────────────
        story += self._keywords_section(ai_report, styles)
        story.append(PageBreak())

        # ── Competitor Analysis ───────────────────────────────────────────────
        if competitor_data:
            story += self._competitor_section(site_data, competitor_data, ai_report, styles)
            story.append(Spacer(1, 0.2 * inch))

        # ── What You're Doing Right ───────────────────────────────────────────
        story += self._wins_section(site_data, styles)
        story.append(Spacer(1, 0.3 * inch))

        # ── Footer CTA ────────────────────────────────────────────────────────
        story += self._footer_cta(ai_report, styles)

        doc.build(story, onFirstPage=self._page_header_footer, onLaterPages=self._page_header_footer)
        return path

    # ── Style Definitions ─────────────────────────────────────────────────────
    def _build_styles(self) -> dict:
        base = getSampleStyleSheet()
        return {
            "h1": ParagraphStyle("h1", parent=base["Normal"], fontSize=28, textColor=WHITE,
                                  fontName="Helvetica-Bold", spaceAfter=6, alignment=TA_CENTER),
            "h2": ParagraphStyle("h2", parent=base["Normal"], fontSize=18, textColor=BRAND_DARK,
                                  fontName="Helvetica-Bold", spaceAfter=8, spaceBefore=4),
            "h3": ParagraphStyle("h3", parent=base["Normal"], fontSize=13, textColor=BRAND_BLUE,
                                  fontName="Helvetica-Bold", spaceAfter=6),
            "body": ParagraphStyle("body", parent=base["Normal"], fontSize=10, textColor=BRAND_DARK,
                                    fontName="Helvetica", spaceAfter=6, leading=14),
            "small": ParagraphStyle("small", parent=base["Normal"], fontSize=8, textColor=LIGHT_GRAY,
                                     fontName="Helvetica", spaceAfter=4),
            "caption": ParagraphStyle("caption", parent=base["Normal"], fontSize=9, textColor=BRAND_DARK,
                                       fontName="Helvetica", spaceAfter=4),
            "center": ParagraphStyle("center", parent=base["Normal"], fontSize=10, alignment=TA_CENTER,
                                      fontName="Helvetica", textColor=BRAND_DARK),
            "score_big": ParagraphStyle("score_big", parent=base["Normal"], fontSize=52,
                                         fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=0),
            "cover_sub": ParagraphStyle("cover_sub", parent=base["Normal"], fontSize=13, textColor=WHITE,
                                         fontName="Helvetica", alignment=TA_CENTER, spaceAfter=4),
            "tag": ParagraphStyle("tag", parent=base["Normal"], fontSize=8, textColor=WHITE,
                                   fontName="Helvetica-Bold", alignment=TA_CENTER),
            "bullet": ParagraphStyle("bullet", parent=base["Normal"], fontSize=10, textColor=BRAND_DARK,
                                      fontName="Helvetica", leftIndent=12, spaceAfter=5, leading=14,
                                      bulletIndent=0, firstLineIndent=-12),
        }

    # ── Cover ─────────────────────────────────────────────────────────────────
    def _cover(self, business_name, url, city, category, site_data, styles) -> list:
        score = site_data.get("overall_score", 0)
        grade = _score_to_grade(score)
        score_col = _score_color(score)
        date_str = datetime.now().strftime("%B %d, %Y")

        cover_bg_data = [[
            Table(
                [[Paragraph("LOCAL SEO AUDIT REPORT", styles["h1"])]],
                colWidths=[7 * inch],
                style=TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), BRAND_BLUE),
                    ("TOPPADDING", (0, 0), (-1, -1), 40),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ("LEFTPADDING", (0, 0), (-1, -1), 20),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 20),
                    ("ROUNDEDCORNERS", (0, 0), (-1, -1), [8, 8, 0, 0]),
                ])
            )
        ]]

        elements = [
            Spacer(1, 0.4 * inch),
            Table(cover_bg_data, colWidths=[7 * inch],
                  style=TableStyle([("TOPPADDING", (0, 0), (-1, -1), 0),
                                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0)])),
        ]

        # Business info card
        info_data = [
            [Paragraph(f"<b>{business_name}</b>", ParagraphStyle("biz", fontSize=20, textColor=BRAND_DARK,
                                                                    fontName="Helvetica-Bold", alignment=TA_CENTER))],
            [Paragraph(f"{url}", ParagraphStyle("url", fontSize=10, textColor=BRAND_BLUE,
                                                 fontName="Helvetica", alignment=TA_CENTER))],
            [Paragraph(f"{category} &nbsp;•&nbsp; {city}", ParagraphStyle("loc", fontSize=11, textColor=LIGHT_GRAY,
                                                                             fontName="Helvetica", alignment=TA_CENTER))],
            [Spacer(1, 0.15 * inch)],
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

        # Score circle simulation with table
        score_style = ParagraphStyle("sc", fontSize=64, fontName="Helvetica-Bold",
                                      textColor=score_col, alignment=TA_CENTER)
        grade_style = ParagraphStyle("gr", fontSize=22, fontName="Helvetica-Bold",
                                      textColor=score_col, alignment=TA_CENTER)
        label_style = ParagraphStyle("lb", fontSize=11, fontName="Helvetica",
                                      textColor=LIGHT_GRAY, alignment=TA_CENTER)

        issues_count = len(site_data.get("issues", []))
        wins_count = len(site_data.get("wins", []))

        score_row = [
            Table([[Paragraph(f"{issues_count}", ParagraphStyle("ic", fontSize=28, fontName="Helvetica-Bold",
                                                                   textColor=BRAND_DANGER, alignment=TA_CENTER)),
                    Paragraph("Issues Found", label_style)]],
                  style=TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6)])),
            Table([[Paragraph(f"{score}", score_style)],
                   [Paragraph(f"Grade: {grade}", grade_style)],
                   [Paragraph("SEO Score", label_style)]],
                  style=TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4)])),
            Table([[Paragraph(f"{wins_count}", ParagraphStyle("wc", fontSize=28, fontName="Helvetica-Bold",
                                                                  textColor=BRAND_SUCCESS, alignment=TA_CENTER)),
                    Paragraph("Strengths Found", label_style)]],
                  style=TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6)])),
        ]

        score_table = Table([score_row], colWidths=[2.1 * inch, 2.8 * inch, 2.1 * inch],
                            style=TableStyle([
                                ("BACKGROUND", (0, 0), (-1, -1), BRAND_LIGHT_BG),
                                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                ("TOPPADDING", (0, 0), (-1, -1), 16),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
                                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                                ("LINEBELOW", (0, 0), (-1, 0), 3, BRAND_BLUE),
                            ]))
        elements.append(score_table)
        elements.append(Spacer(1, 0.15 * inch))

        date_para = Paragraph(f"Prepared: {date_str} &nbsp;&nbsp; | &nbsp;&nbsp; Confidential",
                              ParagraphStyle("date", fontSize=9, textColor=LIGHT_GRAY,
                                             alignment=TA_CENTER, fontName="Helvetica"))
        elements.append(date_para)

        return elements

    # ── Executive Summary ─────────────────────────────────────────────────────
    def _executive_summary(self, site_data, ai_report, styles) -> list:
        elements = [
            Paragraph("Executive Summary", styles["h2"]),
            HRFlowable(width="100%", thickness=2, color=BRAND_BLUE, spaceAfter=10),
        ]

        summary = ai_report.get("summary", "")
        score_interp = ai_report.get("score_interpretation", "")
        if summary:
            elements.append(Paragraph(summary, styles["body"]))
        if score_interp:
            elements.append(Paragraph(f"<i>{score_interp}</i>", styles["body"]))

        critical = ai_report.get("critical_findings", [])
        if critical:
            elements.append(Spacer(1, 0.1 * inch))
            elements.append(Paragraph("Critical Findings", styles["h3"]))
            for finding in critical[:3]:
                elements.append(Paragraph(f"• {finding}", styles["bullet"]))

        return elements

    # ── Score Breakdown ───────────────────────────────────────────────────────
    def _score_breakdown(self, site_data, styles) -> list:
        raw = site_data.get("raw", {})
        score = site_data.get("overall_score", 0)

        categories = [
            ("Technical Foundation", [
                ("HTTPS / SSL", raw.get("https", False)),
                ("Mobile-Friendly (Viewport)", raw.get("has_viewport", False)),
                ("Page Speed < 2s", raw.get("load_time_ms", 9999) < 2000),
            ]),
            ("On-Page SEO", [
                ("Title Tag Present", bool(raw.get("title"))),
                ("Title Length 50-65 chars", 50 <= raw.get("title_length", 0) <= 65),
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
            header_style = ParagraphStyle("ch", fontSize=11, fontName="Helvetica-Bold",
                                           textColor=BRAND_DARK)
            table_data = [
                [Paragraph(f"{cat_name}", header_style),
                 Paragraph(f"{passed}/{total} passed",
                           ParagraphStyle("cp", fontSize=10, fontName="Helvetica",
                                          textColor=BRAND_SUCCESS if passed == total else BRAND_WARNING,
                                          alignment=TA_RIGHT))]
            ]
            for label, passing in checks:
                icon = "✓" if passing else "✗"
                icon_color = BRAND_SUCCESS if passing else BRAND_DANGER
                row = [
                    Paragraph(f"  {label}", styles["caption"]),
                    Paragraph(icon, ParagraphStyle("icon", fontSize=11, fontName="Helvetica-Bold",
                                                    textColor=icon_color, alignment=TA_RIGHT))
                ]
                table_data.append(row)

            t = Table(table_data, colWidths=[5.8 * inch, 1.2 * inch],
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
            elements.append(Spacer(1, 0.12 * inch))

        return elements

    # ── Issues Section ────────────────────────────────────────────────────────
    def _issues_section(self, site_data, styles) -> list:
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
            sev = issue.get("severity", "low")
            grouped.setdefault(sev, []).append(issue)

        for sev in severity_order:
            sev_issues = grouped.get(sev, [])
            if not sev_issues:
                continue

            col = _severity_color(sev)
            label = sev.upper()
            sev_header = Table([[Paragraph(f"  {label} PRIORITY", ParagraphStyle("sl", fontSize=10,
                                                                                   fontName="Helvetica-Bold",
                                                                                   textColor=WHITE))]],
                               colWidths=[7 * inch],
                               style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), col),
                                                 ("TOPPADDING", (0, 0), (-1, -1), 5),
                                                 ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
            elements.append(sev_header)

            for issue in sev_issues:
                row_data = [[Paragraph(f"• {issue['text']}", styles["body"])]]
                row_table = Table(row_data, colWidths=[7 * inch],
                                  style=TableStyle([
                                      ("LEFTPADDING", (0, 0), (-1, -1), 12),
                                      ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                                      ("TOPPADDING", (0, 0), (-1, -1), 5),
                                      ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                                      ("LINEBELOW", (0, 0), (-1, -1), 0.5, BRAND_BORDER),
                                  ]))
                elements.append(row_table)
            elements.append(Spacer(1, 0.08 * inch))

        return elements

    # ── To-Do List ────────────────────────────────────────────────────────────
    def _todo_section(self, ai_report, styles) -> list:
        todos = ai_report.get("todo_list", [])
        if not todos:
            return []

        elements = [
            Paragraph("Your Action Plan", styles["h2"]),
            HRFlowable(width="100%", thickness=2, color=BRAND_BLUE, spaceAfter=10),
            Paragraph(
                "Complete these tasks in order of priority. Each fix will improve your Google ranking.",
                styles["body"]
            ),
            Spacer(1, 0.1 * inch),
        ]

        for item in todos:
            priority = item.get("priority", "?")
            category = item.get("category", "")
            task = item.get("task", "")
            how_to = item.get("how_to", "")
            impact = item.get("impact", "Medium")
            time_est = item.get("time_estimate", "")
            expected = item.get("expected_result", "")

            impact_col = _impact_color(impact)

            # Priority badge + task title
            header_row = [
                Table([[Paragraph(f"#{priority}", ParagraphStyle("pr", fontSize=11,
                                                                    fontName="Helvetica-Bold",
                                                                    textColor=WHITE, alignment=TA_CENTER))]],
                      colWidths=[0.35 * inch],
                      style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), BRAND_BLUE),
                                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6)])),
                Paragraph(f"<b>{task}</b>", ParagraphStyle("tsk", fontSize=11,
                                                              fontName="Helvetica-Bold",
                                                              textColor=BRAND_DARK)),
                Table([[Paragraph(impact, ParagraphStyle("imp", fontSize=8, fontName="Helvetica-Bold",
                                                           textColor=WHITE, alignment=TA_CENTER))]],
                      colWidths=[0.7 * inch],
                      style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), impact_col),
                                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                                        ("ROUNDEDCORNERS", (0, 0), (-1, -1), [4, 4, 4, 4])])),
            ]

            header_table = Table([header_row], colWidths=[0.45 * inch, 5.8 * inch, 0.75 * inch],
                                  style=TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                                    ("BACKGROUND", (0, 0), (-1, -1), BRAND_LIGHT_BG),
                                                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                                                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                                                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                                                    ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))

            detail_rows = []
            if category:
                detail_rows.append([Paragraph(f"<b>Category:</b> {category}", styles["caption"]), ""])
            if time_est:
                detail_rows.append([Paragraph(f"<b>Time needed:</b> {time_est}", styles["caption"]), ""])
            if how_to:
                detail_rows.append([Paragraph(f"<b>How to fix:</b> {how_to}", styles["body"]), ""])
            if expected:
                detail_rows.append([Paragraph(f"<b>Expected result:</b> {expected}", styles["caption"]), ""])

            if detail_rows:
                detail_table = Table(detail_rows, colWidths=[7 * inch, 0],
                                     style=TableStyle([
                                         ("LEFTPADDING", (0, 0), (-1, -1), 12),
                                         ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                                         ("TOPPADDING", (0, 0), (-1, -1), 4),
                                         ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                                         ("LINEBELOW", (0, -1), (-1, -1), 1, BRAND_BORDER),
                                     ]))
            else:
                detail_table = None

            block = [header_table]
            if detail_table:
                block.append(detail_table)
            block.append(Spacer(1, 0.1 * inch))

            elements.append(KeepTogether(block))

        return elements

    # ── Quick Wins ────────────────────────────────────────────────────────────
    def _quick_wins_section(self, ai_report, styles) -> list:
        wins = ai_report.get("quick_wins", [])
        if not wins:
            return []

        elements = [
            Paragraph("Quick Wins (Under 30 Minutes)", styles["h2"]),
            HRFlowable(width="100%", thickness=2, color=BRAND_SUCCESS, spaceAfter=10),
        ]

        rows = [[Paragraph(f"✓ {win}", styles["body"])] for win in wins]
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
    def _keywords_section(self, ai_report, styles) -> list:
        keywords = ai_report.get("keyword_recommendations", [])
        if not keywords:
            return []

        elements = [
            Spacer(1, 0.1 * inch),
            Paragraph("Keyword Recommendations", styles["h2"]),
            HRFlowable(width="100%", thickness=2, color=BRAND_ACCENT, spaceAfter=10),
            Paragraph("Use these keyword phrases in your title tag, meta description, H1, and page content:", styles["body"]),
            Spacer(1, 0.05 * inch),
        ]

        # 2-column keyword grid
        keyword_cells = []
        for i in range(0, len(keywords), 2):
            row = [
                Paragraph(f"→ {keywords[i]}", styles["body"]),
                Paragraph(f"→ {keywords[i+1]}", styles["body"]) if i + 1 < len(keywords) else Paragraph("", styles["body"])
            ]
            keyword_cells.append(row)

        if keyword_cells:
            t = Table(keyword_cells, colWidths=[3.5 * inch, 3.5 * inch],
                      style=TableStyle([
                          ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
                          ("TOPPADDING", (0, 0), (-1, -1), 5),
                          ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                          ("LEFTPADDING", (0, 0), (-1, -1), 10),
                          ("LINEBELOW", (0, 0), (-1, -2), 0.5, BRAND_BORDER),
                      ]))
            elements.append(t)
        return elements

    # ── Competitor Analysis ───────────────────────────────────────────────────
    def _competitor_section(self, site_data, competitor_data, ai_report, styles) -> list:
        elements = [
            Paragraph("Competitor Analysis", styles["h2"]),
            HRFlowable(width="100%", thickness=2, color=BRAND_DARK, spaceAfter=10),
        ]

        # Comparison table
        header = [
            Paragraph("<b>Signal</b>", styles["caption"]),
            Paragraph("<b>Your Site</b>", styles["caption"]),
        ]
        for i, comp in enumerate(competitor_data[:3], 1):
            header.append(Paragraph(f"<b>Competitor {i}</b>", styles["caption"]))

        def yes_no(val):
            return "✓" if val else "✗"

        your_raw = site_data.get("raw", {})
        signals_to_compare = [
            ("SEO Score", str(site_data.get("overall_score", 0)),
             [str(c.get("overall_score", 0)) for c in competitor_data[:3]]),
            ("HTTPS", yes_no(your_raw.get("https")),
             [yes_no(c.get("raw", {}).get("https")) for c in competitor_data[:3]]),
            ("LocalBusiness Schema", yes_no(your_raw.get("has_local_schema")),
             [yes_no(c.get("raw", {}).get("has_local_schema")) for c in competitor_data[:3]]),
            ("Phone on Page", yes_no(your_raw.get("phone_numbers")),
             [yes_no(c.get("raw", {}).get("phone_numbers")) for c in competitor_data[:3]]),
            ("Map Embed", yes_no(your_raw.get("has_map_embed")),
             [yes_no(c.get("raw", {}).get("has_map_embed")) for c in competitor_data[:3]]),
            ("Reviews Content", yes_no(your_raw.get("has_reviews_mention")),
             [yes_no(c.get("raw", {}).get("has_reviews_mention")) for c in competitor_data[:3]]),
            ("Word Count", str(your_raw.get("word_count", 0)),
             [str(c.get("raw", {}).get("word_count", 0)) for c in competitor_data[:3]]),
        ]

        table_data = [header]
        for sig_name, your_val, comp_vals in signals_to_compare:
            row = [Paragraph(sig_name, styles["caption"]), Paragraph(your_val, styles["caption"])]
            for cv in comp_vals:
                row.append(Paragraph(cv, styles["caption"]))
            table_data.append(row)

        n_cols = 2 + min(len(competitor_data), 3)
        col_w = 7.0 / n_cols
        col_widths = [col_w * inch] * n_cols

        t = Table(table_data, colWidths=col_widths,
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

        # Competitor gaps
        gaps = ai_report.get("competitor_gaps", [])
        if gaps:
            elements.append(Spacer(1, 0.15 * inch))
            elements.append(Paragraph("Competitive Gaps to Close", styles["h3"]))
            for gap in gaps:
                elements.append(Paragraph(f"• {gap}", styles["bullet"]))

        return elements

    # ── Wins Section ──────────────────────────────────────────────────────────
    def _wins_section(self, site_data, styles) -> list:
        wins = site_data.get("wins", [])
        if not wins:
            return []

        elements = [
            Paragraph("What You're Already Doing Right", styles["h2"]),
            HRFlowable(width="100%", thickness=2, color=BRAND_SUCCESS, spaceAfter=10),
        ]
        for win in wins:
            elements.append(Paragraph(f"✓ {win}", styles["bullet"]))
        return elements

    # ── Footer CTA ────────────────────────────────────────────────────────────
    def _footer_cta(self, ai_report, styles) -> list:
        close = ai_report.get("motivational_close", "")
        elements = [
            HRFlowable(width="100%", thickness=1, color=BRAND_BORDER, spaceAfter=10),
        ]
        if close:
            cta_style = ParagraphStyle("cta", fontSize=12, fontName="Helvetica-Bold",
                                        textColor=BRAND_BLUE, alignment=TA_CENTER, leading=18)
            elements.append(Paragraph(close, cta_style))
            elements.append(Spacer(1, 0.1 * inch))

        elements.append(Paragraph(
            "This report was generated by LocalSEO Auditor. Implement the fixes above and re-audit in 30 days to measure your improvement.",
            ParagraphStyle("disc", fontSize=8, textColor=LIGHT_GRAY, alignment=TA_CENTER, fontName="Helvetica")
        ))
        return elements

    # ── Page Header/Footer ────────────────────────────────────────────────────
    def _page_header_footer(self, canvas, doc):
        canvas.saveState()
        # Top bar
        canvas.setFillColor(BRAND_BLUE)
        canvas.rect(0, letter[1] - 0.35 * inch, letter[0], 0.35 * inch, fill=1, stroke=0)
        canvas.setFillColor(WHITE)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(0.75 * inch, letter[1] - 0.22 * inch, "LOCAL SEO AUDIT REPORT")
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(
            letter[0] - 0.75 * inch, letter[1] - 0.22 * inch,
            datetime.now().strftime("%B %d, %Y")
        )
        # Bottom bar
        canvas.setFillColor(BRAND_LIGHT_BG)
        canvas.rect(0, 0, letter[0], 0.35 * inch, fill=1, stroke=0)
        canvas.setFillColor(LIGHT_GRAY)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(0.75 * inch, 0.12 * inch, "Confidential — For Business Owner Use Only")
        canvas.drawRightString(letter[0] - 0.75 * inch, 0.12 * inch, f"Page {doc.page}")
        canvas.restoreState()


def _score_to_grade(score: int) -> str:
    if score >= 90: return "A"
    elif score >= 80: return "B"
    elif score >= 70: return "C"
    elif score >= 60: return "D"
    else: return "F"
