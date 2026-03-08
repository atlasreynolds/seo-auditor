"""
AI Analyzer Module
Uses Claude to turn raw SEO data into an actionable, human-readable report.
"""

import os
import re
import json
import anthropic


class AIAnalyzer:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = "claude-opus-4-6"

    def generate_report(
        self,
        business_name: str,
        url: str,
        city: str,
        category: str,
        site_data: dict,
        competitor_data: list[dict],
    ) -> dict:
        prompt = self._build_prompt(
            business_name, url, city, category, site_data, competitor_data
        )

        message = self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            messages=[{"role": "user", "content": prompt}],
        )

        raw_text = message.content[0].text

        try:
            report = _parse_json_response(raw_text)
        except Exception:
            report = {
                "summary": _clean_text(raw_text[:500]),
                "score_interpretation": _default_score_text(site_data.get("overall_score", 0)),
                "critical_findings": [],
                "todo_list": [],
                "quick_wins": [],
                "competitor_gaps": [],
                "keyword_recommendations": [],
                "google_business_tips": [],
                "local_citations": [],
                "content_recommendations": [],
                "motivational_close": "",
            }

        return report

    def _build_prompt(
        self,
        business_name: str,
        url: str,
        city: str,
        category: str,
        site_data: dict,
        competitor_data: list[dict],
    ) -> str:
        score = site_data.get("overall_score", 0)
        issues = site_data.get("issues", [])
        wins = site_data.get("wins", [])
        raw = site_data.get("raw", {})
        bot_protected = site_data.get("bot_protected", False)

        comp_summary = []
        for i, comp in enumerate(competitor_data[:3], 1):
            comp_summary.append({
                "rank": i,
                "url": comp.get("url", ""),
                "score": comp.get("overall_score", 0),
                "issues_count": len(comp.get("issues", [])),
                "wins": comp.get("wins", [])[:5],
                "has_schema": comp.get("raw", {}).get("has_local_schema", False),
                "has_reviews": comp.get("raw", {}).get("has_reviews_mention", False),
                "word_count": comp.get("raw", {}).get("word_count", 0),
            })

        bot_note = ""
        if bot_protected:
            bot_note = "\n⚠️ NOTE: This site appears to be behind Cloudflare or similar bot protection. The scraper could only see the challenge page, not the real site content. Make this a CRITICAL finding and explain what it means for Google indexing.\n"

        prompt = f"""You are a hyper-local SEO expert. A small business owner just paid $49 for a professional SEO audit. Analyze their data and provide actionable recommendations.
{bot_note}
## Business Info
- Business Name: {business_name}
- Website: {url}
- City: {city}
- Category: {category}
- SEO Score: {score}/100

## Their Site Data
**Issues Found ({len(issues)} total):**
{json.dumps(issues, indent=2)}

**What They're Doing Well:**
{json.dumps(wins, indent=2)}

**Technical Signals:**
- Title: "{raw.get('title', 'N/A')}"
- Title Length: {raw.get('title_length', 0)} chars
- Meta Description: "{raw.get('meta_description', 'N/A')[:100]}..."
- H1 Tags: {raw.get('h1_text', [])}
- H2 Count: {raw.get('h2_count', 0)}
- Word Count: {raw.get('word_count', 0)}
- Images Total: {raw.get('total_images', 0)}, Missing Alt: {raw.get('images_missing_alt', 0)}
- Phone on Page: {raw.get('phone_numbers', [])}
- Has LocalBusiness Schema: {raw.get('has_local_schema', False)}
- Has Address: {raw.get('has_address_on_page', False)}
- Has Map Embed: {raw.get('has_map_embed', False)}
- Load Time: {raw.get('load_time_ms', 0)}ms
- HTTPS: {raw.get('https', False)}
- Has Viewport (Mobile): {raw.get('has_viewport', False)}
- Has Reviews Content: {raw.get('has_reviews_mention', False)}

## Top Competitor Data
{json.dumps(comp_summary, indent=2) if comp_summary else "No competitor data available."}

## Your Task
Generate a professional, encouraging, and specific SEO audit report. The business owner is NOT technical — use plain English. Reference their actual city, category, and issues.

Return ONLY valid JSON (no other text, no markdown, no explanation) in this exact structure:

{{
  "summary": "2-3 sentence executive summary of their SEO health, referencing their business name and city",
  "score_interpretation": "1 sentence explaining what their score means competitively",
  "critical_findings": [
    "Plain-English description of the most important problem and why it hurts them"
  ],
  "todo_list": [
    {{
      "priority": 1,
      "category": "one of: Title & Meta, Content, Technical, Local Signals, Schema Markup, Images, Mobile, Speed, Reviews, Google Business",
      "task": "Specific action they must take (imperative, e.g. 'Add your city name to your title tag')",
      "how_to": "Step-by-step instructions a non-technical person can follow",
      "impact": "High / Medium / Low",
      "time_estimate": "e.g. 15 minutes, 1 hour",
      "expected_result": "What will improve after fixing this"
    }}
  ],
  "quick_wins": [
    "3-5 things they can fix in under 30 minutes total"
  ],
  "competitor_gaps": [
    "Specific advantages competitors have over them based on the data"
  ],
  "keyword_recommendations": [
    "Specific keyword phrases they should use in their title, meta, H1, and content — include city + service combinations"
  ],
  "google_business_tips": [
    "Specific actionable tip for optimizing their Google Business Profile — write as complete sentences"
  ],
  "local_citations": [
    "Platform name: Specific action to take to list or claim their business on this platform"
  ],
  "content_recommendations": [
    "Specific content idea they should add to their website — include why it helps local SEO"
  ],
  "motivational_close": "1-2 encouraging sentences about what fixing these issues will do for their business"
}}

Rules:
- Generate 8-15 specific todo items ordered by priority
- Be specific: don't say "add keywords," say "Add '{city} {category}' to your homepage title tag"
- Make how_to instructions genuinely actionable for a non-technical business owner
- Generate 5-8 google_business_tips covering: photos, hours, categories, posts, Q&A, reviews response
- Generate 6-8 local_citations with specific platforms (Google Business Profile, Yelp, Bing Places, Apple Maps, Foursquare, TripAdvisor if restaurant, BBB, Chamber of Commerce)
- Generate 4-6 content_recommendations specific to their business category and city"""

        return prompt


def _parse_json_response(raw_text: str) -> dict:
    """Robustly extract JSON from Claude's response, handling various formats."""
    # Strategy 1: Code block ```json ... ```
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw_text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except Exception:
            pass

    # Strategy 2: Find the outermost { ... } by brace matching
    start = -1
    depth = 0
    for i, ch in enumerate(raw_text):
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start != -1:
                try:
                    return json.loads(raw_text[start:i + 1])
                except Exception:
                    # Keep looking for another JSON object
                    start = -1

    raise ValueError("No valid JSON found in response")


def _clean_text(text: str) -> str:
    """Remove JSON/markdown artifacts from a text field."""
    if not text:
        return text
    text = text.strip()
    # Strip markdown fences
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    # If it looks like raw JSON, try to extract the summary field
    if text.startswith('{'):
        m = re.search(r'"summary"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', text)
        if m:
            return m.group(1).replace('\\"', '"')
    return text.strip()


def _default_score_text(score: int) -> str:
    if score >= 80:
        return "Your site is performing well above average for local SEO."
    elif score >= 60:
        return "Your site has a solid foundation but several gaps are holding you back from top rankings."
    elif score >= 40:
        return "Your site has significant SEO issues that are likely costing you customers every day."
    else:
        return "Your site has critical SEO problems. Fixing these could dramatically increase your visibility in local search."
