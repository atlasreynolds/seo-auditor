import os
import json
import uuid
import stripe
from flask import Flask, render_template, request, jsonify, send_file, session
from flask_cors import CORS
from dotenv import load_dotenv
from modules.scraper import SEOScraper
from modules.ai_analyzer import AIAnalyzer
from modules.pdf_generator import PDFGenerator

load_dotenv(override=True)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-in-prod")
CORS(app)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
AUDIT_PRICE_CENTS = 4900  # $49.00

# ── File-based audit store (survives across gunicorn workers) ─────────────────
AUDIT_DIR = "/tmp/ar_audits"
os.makedirs(AUDIT_DIR, exist_ok=True)


def _save_audit(audit_id: str, data: dict):
    with open(os.path.join(AUDIT_DIR, f"{audit_id}.json"), "w") as f:
        json.dump(data, f)


def _load_audit(audit_id: str) -> dict | None:
    path = os.path.join(AUDIT_DIR, f"{audit_id}.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


@app.route("/")
def index():
    return render_template("index.html", stripe_key=STRIPE_PUBLISHABLE_KEY)


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/api/audit/preview", methods=["POST"])
def audit_preview():
    """Run a free preview (limited data) to hook the user before payment."""
    data = request.get_json()
    url = data.get("url", "").strip()
    business_name = data.get("business_name", "").strip()
    city = data.get("city", "").strip()
    category = data.get("category", "").strip()

    if not url or not business_name:
        return jsonify({"error": "URL and business name are required"}), 400

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        scraper = SEOScraper()
        site_data = scraper.analyze(url)
        score = site_data.get("overall_score", 0)
        issues_count = len(site_data.get("issues", []))

        # Return teaser data only
        preview = {
            "score": score,
            "grade": _score_to_grade(score),
            "issues_found": issues_count,
            "top_3_issues": site_data.get("issues", [])[:3],
            "business_name": business_name,
            "url": url,
        }

        # Store full data keyed by a session token for after payment
        audit_id = str(uuid.uuid4())
        _save_audit(audit_id, {
            "url": url,
            "business_name": business_name,
            "city": city,
            "category": category,
            "site_data": site_data,
            "paid": False,
        })

        return jsonify({"preview": preview, "audit_id": audit_id})

    except Exception as e:
        return jsonify({"error": f"Could not analyze site: {str(e)}"}), 500


@app.route("/api/payment/create-intent", methods=["POST"])
def create_payment_intent():
    """Create a Stripe PaymentIntent for the $49 audit fee."""
    data = request.get_json()
    audit_id = data.get("audit_id")

    audit = _load_audit(audit_id) if audit_id else None
    if not audit:
        return jsonify({"error": "Invalid audit session"}), 400

    try:
        intent = stripe.PaymentIntent.create(
            amount=AUDIT_PRICE_CENTS,
            currency="usd",
            metadata={"audit_id": audit_id},
            automatic_payment_methods={"enabled": True},
        )
        return jsonify({"client_secret": intent.client_secret})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/payment/confirm", methods=["POST"])
def confirm_payment():
    """Called after successful Stripe payment to trigger full AI audit."""
    data = request.get_json()
    payment_intent_id = data.get("payment_intent_id")
    audit_id = data.get("audit_id")

    audit = _load_audit(audit_id) if audit_id else None
    if not audit:
        return jsonify({"error": "Invalid audit session"}), 400

    try:
        # Verify payment with Stripe
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        if intent.status != "succeeded":
            return jsonify({"error": "Payment not completed"}), 402

        if intent.metadata.get("audit_id") != audit_id:
            return jsonify({"error": "Payment mismatch"}), 400

        audit["paid"] = True

        # Run full competitor analysis + AI report
        scraper = SEOScraper()
        competitors = scraper.find_competitors(
            audit["business_name"], audit["city"], audit["category"]
        )
        competitor_data = []
        for comp_url in competitors[:3]:
            try:
                comp_analysis = scraper.analyze(comp_url, quick=True)
                competitor_data.append(comp_analysis)
            except Exception:
                pass

        # Generate AI report
        analyzer = AIAnalyzer()
        ai_report = analyzer.generate_report(
            business_name=audit["business_name"],
            url=audit["url"],
            city=audit["city"],
            category=audit["category"],
            site_data=audit["site_data"],
            competitor_data=competitor_data,
        )

        audit["ai_report"] = ai_report
        audit["competitor_data"] = competitor_data

        # Generate PDF
        pdf_gen = PDFGenerator()
        pdf_path = pdf_gen.create_report(
            audit_id=audit_id,
            business_name=audit["business_name"],
            url=audit["url"],
            city=audit["city"],
            category=audit["category"],
            site_data=audit["site_data"],
            competitor_data=competitor_data,
            ai_report=ai_report,
        )
        audit["pdf_path"] = pdf_path
        _save_audit(audit_id, audit)

        return jsonify({"success": True, "audit_id": audit_id})

    except stripe.error.StripeError as e:
        return jsonify({"error": str(e)}), 402
    except Exception as e:
        return jsonify({"error": f"Audit generation failed: {str(e)}"}), 500


@app.route("/api/audit/demo", methods=["POST"])
def audit_demo():
    """Run a full audit in demo mode (no payment required). For testing."""
    if os.getenv("DEMO_MODE", "false").lower() != "true":
        return jsonify({"error": "Demo mode is disabled"}), 403

    data = request.get_json()
    url = data.get("url", "").strip()
    business_name = data.get("business_name", "Your Business")
    city = data.get("city", "")
    category = data.get("category", "")

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        audit_id = str(uuid.uuid4())
        scraper = SEOScraper()
        site_data = scraper.analyze(url)
        competitors = scraper.find_competitors(business_name, city, category)
        competitor_data = []
        for comp_url in competitors[:3]:
            try:
                competitor_data.append(scraper.analyze(comp_url))
            except Exception:
                pass

        analyzer = AIAnalyzer()
        ai_report = analyzer.generate_report(
            business_name=business_name,
            url=url,
            city=city,
            category=category,
            site_data=site_data,
            competitor_data=competitor_data,
        )

        pdf_gen = PDFGenerator()
        pdf_path = pdf_gen.create_report(
            audit_id=audit_id,
            business_name=business_name,
            url=url,
            city=city,
            category=category,
            site_data=site_data,
            competitor_data=competitor_data,
            ai_report=ai_report,
        )

        _save_audit(audit_id, {
            "pdf_path": pdf_path,
            "paid": True,
            "business_name": business_name,
        })

        return jsonify({"success": True, "audit_id": audit_id})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/audit/download/<audit_id>")
def download_report(audit_id):
    """Download the generated PDF report."""
    audit = _load_audit(audit_id)
    if not audit:
        return jsonify({"error": "Report not found"}), 404
    if not audit.get("paid"):
        return jsonify({"error": "Payment required"}), 402

    pdf_path = audit.get("pdf_path")
    if not pdf_path or not os.path.exists(pdf_path):
        return jsonify({"error": "Report file not found"}), 404

    business_name = audit.get("business_name", "business").replace(" ", "_")
    return send_file(
        pdf_path,
        as_attachment=True,
        download_name=f"SEO_Audit_{business_name}.pdf",
        mimetype="application/pdf",
    )


def _score_to_grade(score):
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"


if __name__ == "__main__":
    os.makedirs("reports", exist_ok=True)
    port = int(os.getenv("PORT", 5000))
    app.run(debug=True, port=port)
