# LocalSEO Auditor

A $49/audit SaaS that scans a local business website, compares it to top 3 competitors, and generates a professional PDF "fix list" report powered by Claude AI.

## What It Does

1. Business owner enters their URL, name, city, and category
2. Free preview: instant SEO score + top 3 issues (no payment)
3. Pay $49 via Stripe → full AI-generated report downloads as PDF
4. Report includes: prioritized to-do list, competitor comparison, keyword recommendations, quick wins

## Setup

### 1. Install dependencies

```bash
cd seo-auditor
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in:
- `ANTHROPIC_API_KEY` — get from https://console.anthropic.com
- `STRIPE_SECRET_KEY` + `STRIPE_PUBLISHABLE_KEY` — get from https://dashboard.stripe.com/apikeys
  - Use `sk_test_` / `pk_test_` keys during development
- `FLASK_SECRET_KEY` — any random string

### 3. Run

```bash
python app.py
```

Visit http://localhost:5000

## Testing Without Stripe

Set `DEMO_MODE=true` in your `.env` file. This skips payment entirely and runs the full audit on button click. Great for testing the full flow and PDF output.

## Architecture

```
app.py                    # Flask routes
modules/
  scraper.py              # Fetches & analyzes 20+ SEO signals per site
  ai_analyzer.py          # Feeds data to Claude, gets structured report JSON
  pdf_generator.py        # Builds branded PDF with ReportLab
templates/
  index.html              # Full single-page frontend (Tailwind + Stripe.js)
reports/                  # Generated PDFs stored here (created at runtime)
```

## Audit Flow

```
User submits form
    → POST /api/audit/preview
    → scraper.analyze(url)          # 20+ SEO checks
    → Returns: score, grade, top 3 issues

User clicks "Unlock Full Report"
    → POST /api/payment/create-intent
    → Stripe PaymentIntent created ($49)
    → Stripe.js collects card + confirms

Payment succeeds
    → POST /api/payment/confirm
    → Stripe payment verified server-side
    → scraper.find_competitors()    # Google search for top 3 competitors
    → scraper.analyze() × 3        # Analyze each competitor
    → ai_analyzer.generate_report() # Claude writes the fix list
    → pdf_generator.create_report() # Builds the PDF
    → GET /api/audit/download/:id  # User downloads PDF
```

## Monetization

- **Price:** $49/audit (one-time)
- **Cost per audit:** ~$0.30–0.80 (Claude API + hosting)
- **Margin:** ~98%
- **Stripe fees:** ~$1.72 per transaction (2.9% + $0.30)

## Production Deployment

### Fly.io (recommended, ~$5/month)

```bash
brew install flyctl
fly launch
fly secrets set ANTHROPIC_API_KEY=sk-ant-... STRIPE_SECRET_KEY=sk_live_... STRIPE_PUBLISHABLE_KEY=pk_live_... FLASK_SECRET_KEY=your-secret
fly deploy
```

### Important for production:
- Replace in-memory `audit_store` dict in `app.py` with Redis or a database
- Add a proper job queue (Celery + Redis) for the full audit — it can take 60s
- Set up proper logging and error monitoring (Sentry)
- Configure Stripe webhooks for payment reliability

## SEO Signals Checked (20+)

| Signal | Category |
|--------|----------|
| HTTPS / SSL | Technical |
| Mobile viewport tag | Technical |
| Page load speed | Technical |
| Title tag presence + length | On-Page |
| Meta description presence + length | On-Page |
| H1 count (should be exactly 1) | On-Page |
| H2 subheadings | On-Page |
| Image alt text coverage | On-Page |
| Word count | Content |
| Internal links | Content |
| Open Graph tags | Social |
| LocalBusiness schema markup | Local |
| Phone number on page | Local |
| Street address on page | Local |
| Google Maps embed | Local |
| Reviews/testimonials content | Local |
| Contact page link | Local |
| Favicon | Branding |

## Customization

- **Pricing:** Change `AUDIT_PRICE_CENTS = 4900` in `app.py`
- **Business categories:** Edit the `<select>` in `templates/index.html`
- **SEO signals:** Add checks in `modules/scraper.py`
- **Report branding:** Edit colors at the top of `modules/pdf_generator.py`
- **AI prompt:** Edit `_build_prompt()` in `modules/ai_analyzer.py`
