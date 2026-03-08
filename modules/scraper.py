"""
SEO Scraper Module
Analyzes a website for 20+ SEO signals relevant to local search ranking.
Also discovers top competitors via Google search.
"""

import re
import time
import json
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}

# Indicators that the page is a bot-protection challenge, not real content
BOT_PROTECTION_SIGNALS = [
    "just a moment", "checking your browser", "cf-browser-verification",
    "cf-challenge", "ddos-guard", "enable javascript and cookies",
    "verify you are human", "please wait", "ray id",
]

TIMEOUT = 15

# JS-framework fingerprints — these sites render content client-side so
# BeautifulSoup sees mostly empty HTML even when real content exists.
JS_FRAMEWORK_SIGNALS = [
    "wix.com", "parastorage.com",          # Wix
    "squarespace.com",                      # Squarespace
    "weebly.com",                           # Weebly
    "shopify.com",                          # Shopify
    "godaddy.com/gdcorp",                   # GoDaddy Website Builder
    "editmysite.com",                       # GoDaddy / Weebly
    "jimdo.com",                            # Jimdo
]

# Secondary paths to try when homepage NAP signals are unverifiable
NAP_FALLBACK_PATHS = ["/contact", "/contact-us", "/about", "/about-us",
                      "/hours", "/location", "/find-us", "/info"]


class SEOScraper:
    def analyze(self, url: str) -> dict:
        """
        Fetch a URL and return a structured dict of SEO signals.
        Returns a score (0–100) and a list of issues.
        """
        result = {
            "url": url,
            "reachable": False,
            "overall_score": 0,
            "issues": [],
            "wins": [],
            "raw": {},
        }

        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
            result["reachable"] = True
            result["status_code"] = resp.status_code
            result["final_url"] = resp.url
            result["load_time_ms"] = int(resp.elapsed.total_seconds() * 1000)
        except requests.exceptions.RequestException as e:
            result["issues"].append({"severity": "critical", "text": f"Site unreachable: {str(e)}"})
            return result

        html = resp.text
        soup = BeautifulSoup(html, "html.parser")

        # ── Bot / Cloudflare protection check ────────────────────────────────
        html_lower = html.lower()
        title_tag_early = soup.find("title")
        title_lower = title_tag_early.get_text().lower() if title_tag_early else ""
        bot_protected = any(
            sig in title_lower or sig in html_lower
            for sig in BOT_PROTECTION_SIGNALS
        )
        result["bot_protected"] = bot_protected

        signals = {}
        issues = []
        wins = []

        if bot_protected:
            issues.append({
                "severity": "critical",
                "text": (
                    "Bot protection detected (likely Cloudflare) — Google's crawler and your "
                    "customers may be seeing a challenge page instead of your actual website. "
                    "This could be severely limiting your search visibility. Contact your hosting "
                    "provider to whitelist Googlebot, or disable the challenge for regular visitors."
                )
            })

        # ── 1. HTTPS ────────────────────────────────────────────────────────
        uses_https = result["final_url"].startswith("https://")
        signals["https"] = uses_https
        if uses_https:
            wins.append("Site uses HTTPS (secure)")
        else:
            issues.append({"severity": "critical", "text": "Site does not use HTTPS — Google penalizes insecure sites"})

        # ── 2. Title Tag ─────────────────────────────────────────────────────
        title_tag = soup.find("title")
        title_text = title_tag.get_text(strip=True) if title_tag else ""
        signals["title"] = title_text
        signals["title_length"] = len(title_text)
        if not title_text:
            issues.append({"severity": "critical", "text": "Missing <title> tag — this is the #1 on-page SEO factor"})
        elif len(title_text) < 30:
            issues.append({"severity": "high", "text": f"Title tag is too short ({len(title_text)} chars). Aim for 50–60 characters with your city and service"})
        elif len(title_text) > 65:
            issues.append({"severity": "medium", "text": f"Title tag is too long ({len(title_text)} chars). Keep it under 65 characters or Google will truncate it"})
        else:
            wins.append(f"Title tag is well-sized ({len(title_text)} chars)")

        # ── 3. Meta Description ───────────────────────────────────────────────
        meta_desc = soup.find("meta", attrs={"name": "description"})
        desc_text = meta_desc["content"].strip() if meta_desc and meta_desc.get("content") else ""
        signals["meta_description"] = desc_text
        signals["meta_description_length"] = len(desc_text)
        if not desc_text:
            issues.append({"severity": "high", "text": "Missing meta description — add a 150–160 character summary with your location and services"})
        elif len(desc_text) < 70:
            issues.append({"severity": "medium", "text": f"Meta description is too short ({len(desc_text)} chars). Aim for 150–160 characters"})
        elif len(desc_text) > 165:
            issues.append({"severity": "low", "text": f"Meta description too long ({len(desc_text)} chars). Google truncates at ~160 characters"})
        else:
            wins.append("Meta description length is good")

        # ── 4. H1 Tag ─────────────────────────────────────────────────────────
        h1_tags = soup.find_all("h1")
        signals["h1_count"] = len(h1_tags)
        signals["h1_text"] = [h.get_text(strip=True) for h in h1_tags]
        if len(h1_tags) == 0:
            issues.append({"severity": "high", "text": "No H1 heading found — add one H1 that includes your primary service and city"})
        elif len(h1_tags) > 1:
            issues.append({"severity": "medium", "text": f"Multiple H1 tags ({len(h1_tags)}) found — use exactly one H1 per page"})
        else:
            wins.append(f"Has exactly one H1: \"{h1_tags[0].get_text(strip=True)[:60]}\"")

        # ── 5. H2 Tags ────────────────────────────────────────────────────────
        h2_tags = soup.find_all("h2")
        signals["h2_count"] = len(h2_tags)
        if len(h2_tags) == 0:
            issues.append({"severity": "low", "text": "No H2 subheadings — structure your content with H2s for each service/section"})
        else:
            wins.append(f"Has {len(h2_tags)} H2 subheadings")

        # ── 6. Images & Alt Text ─────────────────────────────────────────────
        images = soup.find_all("img")
        images_missing_alt = [img for img in images if not img.get("alt", "").strip()]
        signals["total_images"] = len(images)
        signals["images_missing_alt"] = len(images_missing_alt)
        if images_missing_alt:
            issues.append({
                "severity": "high",
                "text": f"{len(images_missing_alt)} of {len(images)} images are missing alt text — alt text helps Google understand your images and improves accessibility"
            })
        elif images:
            wins.append(f"All {len(images)} images have alt text")

        # ── 7. Page Speed (load time proxy) ──────────────────────────────────
        load_ms = result.get("load_time_ms", 0)
        signals["load_time_ms"] = load_ms
        if load_ms > 3000:
            issues.append({"severity": "high", "text": f"Slow page load ({load_ms}ms). Google penalizes slow sites — aim for under 2 seconds"})
        elif load_ms > 1500:
            issues.append({"severity": "medium", "text": f"Page load time could be faster ({load_ms}ms). Aim for under 1.5 seconds"})
        else:
            wins.append(f"Fast page load time ({load_ms}ms)")

        # ── 8. Viewport / Mobile-Friendly ────────────────────────────────────
        viewport = soup.find("meta", attrs={"name": "viewport"})
        signals["has_viewport"] = bool(viewport)
        if not viewport:
            issues.append({"severity": "critical", "text": "No viewport meta tag — your site likely looks broken on mobile phones. Google uses mobile-first indexing"})
        else:
            wins.append("Has viewport meta tag (mobile-friendly)")

        # ── 9. Local Business Schema ──────────────────────────────────────────
        schema_tags = soup.find_all("script", attrs={"type": "application/ld+json"})
        has_local_schema = False
        schema_types = []
        for tag in schema_tags:
            try:
                data = json.loads(tag.string or "")
                schema_type = data.get("@type", "")
                schema_types.append(schema_type)
                if schema_type in ("LocalBusiness", "Restaurant", "MedicalBusiness",
                                   "Dentist", "Plumber", "RealEstateAgent", "Store",
                                   "HealthAndBeautyBusiness", "FoodEstablishment"):
                    has_local_schema = True
            except Exception:
                pass
        signals["has_local_schema"] = has_local_schema
        signals["schema_types"] = schema_types
        if not has_local_schema:
            issues.append({
                "severity": "high",
                "text": "No LocalBusiness schema markup found — schema markup tells Google exactly what your business is and where it's located"
            })
        else:
            wins.append(f"Has LocalBusiness schema markup ({', '.join(schema_types)})")

        # ── 10. NAP (Name, Address, Phone) ────────────────────────────────────
        page_text = soup.get_text(" ", strip=True)

        # Detect JS-rendered frameworks — content won't be in static HTML
        is_js_rendered = any(sig in html for sig in JS_FRAMEWORK_SIGNALS)
        signals["is_js_rendered"] = is_js_rendered

        # Content is unverifiable if bot-protected OR JS-rendered with very thin text
        page_word_count_raw = len(page_text.split())
        content_unverifiable = bot_protected or (is_js_rendered and page_word_count_raw < 150)
        signals["content_unverifiable"] = content_unverifiable

        phone_pattern = re.compile(
            r'(\+?1?[\s\-\.]?\(?\d{3}\)?[\s\-\.]?\d{3}[\s\-\.]?\d{4})'
        )

        # Phone: check visible text, tel: links, AND inline <script> tag contents
        text_phones = phone_pattern.findall(page_text)
        tel_links = soup.find_all("a", href=re.compile(r'^tel:', re.I))
        tel_phones = [
            a["href"].replace("tel:", "").replace("tel:+1", "+1").strip()
            for a in tel_links if a.get("href")
        ]
        # Also search script tag contents (Wix/Squarespace embed data in JS)
        script_phones = []
        for script in soup.find_all("script"):
            script_text = script.string or ""
            if len(script_text) > 20:
                script_phones += phone_pattern.findall(script_text)

        phones = list(dict.fromkeys(tel_phones + text_phones + script_phones))[:3]
        signals["phone_numbers"] = phones

        # Address: check text keywords, zip codes, microdata/schema
        address_keywords = [
            "street", "st.", "st,", "ave", "avenue", "blvd", "boulevard",
            "drive", "dr.", "dr,", "road", "rd.", "rd,", "suite", "ste",
            "lane", "ln.", "court", "ct.", "place", "pl.", "way", "hwy",
            "highway", "pkwy", "parkway", "floor", "building",
        ]
        zip_pattern = re.compile(r'\b\d{5}(?:-\d{4})?\b')
        has_zip = bool(zip_pattern.search(page_text))
        addr_microdata = soup.find(attrs={"itemprop": re.compile(r'streetAddress|address', re.I)})
        has_address = (
            has_zip
            or bool(addr_microdata)
            or any(kw in page_text.lower() for kw in address_keywords)
        )

        # ── Hours of operation detection ──────────────────────────────────────
        hours_patterns = [
            re.compile(r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', re.I),
            re.compile(r'\b\d{1,2}(:\d{2})?\s*(am|pm)\b', re.I),
            re.compile(r'\bhours\s*[:\-]', re.I),
            re.compile(r'\bopen\s+(daily|7\s*days|monday)', re.I),
            re.compile(r'\bclosed\s+on\b', re.I),
        ]
        has_hours = any(p.search(page_text) for p in hours_patterns)

        # ── Menu detection ────────────────────────────────────────────────────
        menu_links = [
            a for a in all_links if a.get("href") and
            any(kw in (a.get("href", "") + a.get_text("", strip=True)).lower()
                for kw in ["menu", "food", "drink", "specials"])
        ]
        has_menu = bool(menu_links) or any(
            kw in page_text.lower() for kw in ["our menu", "view menu", "full menu", "menu items"]
        )

        # ── Secondary page fallback for unverifiable / thin content ───────────
        if content_unverifiable or (not phones and not has_address):
            sec_text, sec_tel = self._fetch_secondary_nap(url)
            if sec_text:
                if not phones:
                    text_phones2 = phone_pattern.findall(sec_text)
                    phones = list(dict.fromkeys(sec_tel + text_phones2))[:3]
                if not has_address:
                    has_address = (
                        bool(zip_pattern.search(sec_text))
                        or any(kw in sec_text.lower() for kw in address_keywords)
                    )
                if not has_hours:
                    has_hours = any(p.search(sec_text) for p in hours_patterns)
                if not has_menu:
                    has_menu = any(kw in sec_text.lower()
                                   for kw in ["our menu", "view menu", "full menu"])

        signals["has_address_on_page"] = has_address
        signals["has_hours"] = has_hours
        signals["has_menu"] = has_menu

        # ── Issue flags — softened when content could not be verified ─────────
        unverifiable_suffix = (
            " (Note: your site's security settings or JavaScript rendering may have "
            "prevented our scanner from verifying this — please confirm manually)"
        )

        if not phones:
            text = "No phone number visible on page — local customers need to call you easily. Add your phone prominently"
            if content_unverifiable:
                text += unverifiable_suffix
            issues.append({"severity": "high", "text": text})
        else:
            wins.append(f"Phone number found: {phones[0]}")

        if not has_address:
            text = "No street address found on page — your physical address helps Google verify your local presence"
            if content_unverifiable:
                text += unverifiable_suffix
            issues.append({"severity": "high", "text": text})
        else:
            wins.append("Street address detected on page")

        # ── 11. Google Maps / Embed ────────────────────────────────────────────
        has_map = "google.com/maps" in html or "maps.google" in html
        signals["has_map_embed"] = has_map
        if not has_map:
            issues.append({"severity": "medium", "text": "No Google Maps embed found — embedding a map reinforces your local presence to Google"})
        else:
            wins.append("Google Maps embed found")

        # ── 12. Internal Links ────────────────────────────────────────────────
        base_domain = urlparse(url).netloc
        all_links = soup.find_all("a", href=True)
        internal_links = [
            a for a in all_links
            if urlparse(urljoin(url, a["href"])).netloc == base_domain
        ]
        signals["internal_link_count"] = len(internal_links)
        if len(internal_links) < 3:
            issues.append({"severity": "low", "text": f"Only {len(internal_links)} internal links found — link between your pages to help Google crawl your site"})
        else:
            wins.append(f"{len(internal_links)} internal links found")

        # ── 13. Word Count ────────────────────────────────────────────────────
        words = page_text.split()
        signals["word_count"] = len(words)
        if not content_unverifiable:
            if len(words) < 300:
                issues.append({"severity": "medium", "text": f"Very thin content ({len(words)} words). Pages with 300+ words rank much better — describe your services in detail"})
            elif len(words) > 500:
                wins.append(f"Good content depth ({len(words)} words)")

        # ── 14. Open Graph Tags ───────────────────────────────────────────────
        og_title = soup.find("meta", property="og:title")
        og_desc = soup.find("meta", property="og:description")
        og_image = soup.find("meta", property="og:image")
        signals["has_og_title"] = bool(og_title)
        signals["has_og_description"] = bool(og_desc)
        signals["has_og_image"] = bool(og_image)
        if not og_title or not og_image:
            issues.append({"severity": "low", "text": "Missing Open Graph tags — these control how your site appears when shared on Facebook/social media"})
        else:
            wins.append("Open Graph tags present (good social sharing)")

        # ── 15. Favicon ───────────────────────────────────────────────────────
        favicon = soup.find("link", rel=lambda r: r and "icon" in " ".join(r).lower())
        signals["has_favicon"] = bool(favicon)
        if not favicon:
            issues.append({"severity": "low", "text": "No favicon detected — a favicon improves brand recognition in browser tabs and Google results"})

        # ── 16. Contact Page ──────────────────────────────────────────────────
        has_contact = any(
            "contact" in a["href"].lower() or "contact" in a.get_text("", strip=True).lower()
            for a in all_links if a.get("href")
        )
        signals["has_contact_link"] = has_contact
        if not has_contact:
            issues.append({"severity": "medium", "text": "No Contact page link found — a dedicated contact page is a local SEO best practice"})
        else:
            wins.append("Contact page link present")

        # ── 17. Reviews / Testimonials Keywords ──────────────────────────────
        review_keywords = ["review", "testimonial", "rating", "5-star", "five star", "★"]
        has_reviews = any(kw in page_text.lower() for kw in review_keywords)
        signals["has_reviews_mention"] = has_reviews
        if not has_reviews:
            issues.append({"severity": "medium", "text": "No reviews or testimonials visible on page — social proof boosts conversions and signals trust to Google"})
        else:
            wins.append("Reviews/testimonials content found")

        # ── Calculate Score ───────────────────────────────────────────────────
        score = _calculate_score(issues)
        result["overall_score"] = score
        result["issues"] = issues
        result["wins"] = wins
        result["raw"] = signals

        return result

    def _fetch_secondary_nap(self, url: str) -> tuple:
        """
        Try secondary pages (/contact, /about, etc.) to find NAP signals
        that may not be on the homepage (common with JS-rendered sites).
        Returns (combined_text, tel_links_list).
        """
        base = urlparse(url)
        combined_text = ""
        combined_tel = []
        for path in NAP_FALLBACK_PATHS:
            try:
                test_url = f"{base.scheme}://{base.netloc}{path}"
                resp = requests.get(test_url, headers=HEADERS, timeout=8, allow_redirects=True)
                if resp.status_code == 200 and len(resp.text) > 500:
                    page_soup = BeautifulSoup(resp.text, "html.parser")
                    page_lower = resp.text.lower()
                    if any(s in page_lower for s in BOT_PROTECTION_SIGNALS):
                        continue
                    combined_text += " " + page_soup.get_text(" ", strip=True)
                    for a in page_soup.find_all("a", href=re.compile(r'^tel:', re.I)):
                        if a.get("href"):
                            combined_tel.append(a["href"].replace("tel:", "").strip())
            except Exception:
                continue
        return combined_text.strip(), combined_tel

    def find_competitors(self, business_name: str, city: str, category: str) -> list[str]:
        """
        Find top competitor URLs via Google search scraping.
        Falls back gracefully if blocked.
        """
        query = f"{category} {city} near me"
        urls = []

        try:
            search_url = f"https://www.google.com/search?q={requests.utils.quote(query)}&num=10"
            resp = requests.get(search_url, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")

            # Extract organic result links
            for a in soup.select("a[href]"):
                href = a["href"]
                if href.startswith("/url?q="):
                    actual_url = href.split("/url?q=")[1].split("&")[0]
                    parsed = urlparse(actual_url)
                    if parsed.scheme in ("http", "https") and parsed.netloc:
                        # Skip known non-business sites
                        skip_domains = ["google.com", "youtube.com", "facebook.com",
                                        "yelp.com", "yellowpages.com", "bbb.org",
                                        "wikipedia.org", "reddit.com"]
                        if not any(d in parsed.netloc for d in skip_domains):
                            urls.append(actual_url)
                            if len(urls) >= 5:
                                break

        except Exception:
            pass

        return urls[:3]


def _calculate_score(issues: list) -> int:
    """Deduct points based on issue severity."""
    score = 100
    deductions = {"critical": 15, "high": 8, "medium": 4, "low": 2}
    for issue in issues:
        score -= deductions.get(issue["severity"], 2)
    return max(0, min(100, score))
