#!/usr/bin/env python3
from __future__ import annotations

import io
import os
import re
import tempfile
import zipfile
from datetime import datetime
import time
from flask import Flask, render_template, request, send_file, redirect, url_for, flash, Response, session, abort
from typing import Optional

from .scribe_optimize import optimize_pdf
from .scribe_epub import pdf_to_epub
from .paywall import init_db, is_active, set_subscription

try:
    import stripe  # type: ignore
except Exception:
    stripe = None

app = Flask(__name__)
app.secret_key = os.environ.get("SCRIBE_UI_SECRET", "dev-secret-key")
app.config["SESSION_COOKIE_NAME"] = "scribe_ui"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_CONTENT_LENGTH", str(50 * 1024 * 1024)))  # 50MB default
if os.environ.get("BASE_URL", "").startswith("https://"):
    app.config["SESSION_COOKIE_SECURE"] = True

init_db()

STRIPE_SECRET = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID")  # £2/month price id
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")
BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5000")
TEST_MODE = os.environ.get("PAYWALL_TEST_MODE", "0").lower() in ("1", "true", "yes", "on")
import secrets


def _validate_production_config():
    """Validate required configuration for production mode"""
    if not TEST_MODE:
        missing_config = []
        if not STRIPE_SECRET:
            missing_config.append("STRIPE_SECRET_KEY")
        if not STRIPE_PRICE_ID:
            missing_config.append("STRIPE_PRICE_ID")
        if not STRIPE_WEBHOOK_SECRET:
            missing_config.append("STRIPE_WEBHOOK_SECRET")
        if not stripe:
            missing_config.append("stripe library")
        
        if missing_config:
            import sys
            print(f"WARNING: Production mode requires: {', '.join(missing_config)}", file=sys.stderr)
            print("Conversion endpoints will return 503 Service Unavailable", file=sys.stderr)


# Validate configuration on startup
_validate_production_config()


def _ensure_csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def _require_csrf():
    token = session.get("csrf_token") or ""
    form_token = request.form.get("csrf_token", "")
    if not token or not form_token or not secrets.compare_digest(token, form_token):
        abort(403)


def _require_active_subscription():
    """Ensure user has an active subscription. For POST requests, returns 402 Payment Required.
    For GET requests, redirects to pricing page."""
    if TEST_MODE:
        # In test mode, auto-activate a dummy subscription for the session
        if not session.get("customer_id"):
            session["customer_id"] = "test_customer"
        # Ensure DB has an active row with a long-lived period end
        try:
            set_subscription("test_customer", "test@example.com", "active", int(time.time()) + 3600 * 24 * 365 * 10)
        except Exception:
            pass
        return True
    
    # In production mode, check Stripe configuration
    if not (stripe and STRIPE_SECRET and STRIPE_PRICE_ID):
        if request.method == "POST":
            return ("Service temporarily unavailable - payment system not configured.", 503)
        else:
            return ("Service temporarily unavailable - payment system not configured.", 503)
    
    customer_id = session.get("customer_id")
    if not customer_id or not is_active(customer_id):
        if request.method == "POST":
            # For POST requests (file processing), return 402 Payment Required
            return ("Payment Required: Please subscribe to use conversion features.", 402)
        else:
            # For GET requests, redirect to pricing
            return redirect(url_for("pricing"))
    return True


@app.after_request
def _set_security_headers(resp: Response) -> Response:
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    resp.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'",
    )
    return resp
if stripe and STRIPE_SECRET:
    stripe.api_key = STRIPE_SECRET


@app.route("/favicon.ico")
def favicon() -> Response:
    # 1x1 transparent PNG to avoid 404 noise; replace with a real icon later if desired
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\x0cIDAT\x08\x99c\x00\x01\x00\x00\x05\x00\x01\x0d\n\x2dB\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    return Response(png_bytes, mimetype="image/png")


@app.route("/", methods=["GET", "POST"])
def index():
    _ensure_csrf_token()
    
    # Enforce subscription requirement for both GET and POST
    subscription_check = _require_active_subscription()
    if subscription_check is not True:
        return subscription_check
    
    if request.method == "POST":
        _require_csrf()
        file = request.files.get("pdf")
        if not file or not file.filename.lower().endswith(".pdf"):
            flash("Please upload a PDF file.", "error")
            return redirect(url_for("index"))

        # Quick PDF magic header check
        try:
            head = file.stream.read(5)
            file.stream.seek(0)
        except Exception:
            head = b""
        if not head.startswith(b"%PDF-"):
            flash("File does not look like a PDF.", "error")
            return redirect(url_for("index"))

        def clamp_int(val_str: Optional[str], default: int, lo: int, hi: int) -> int:
            try:
                v = int(val_str) if val_str is not None and val_str != "" else default
            except ValueError:
                v = default
            return max(lo, min(hi, v))

        page_size = request.form.get("page_size", "scribe")
        margin_pt = clamp_int(request.form.get("margin_pt"), 14, 0, 200)
        dpi = clamp_int(request.form.get("dpi"), 300, 72, 600)
        crop = request.form.get("crop") == "on"
        autocontrast = request.form.get("autocontrast") == "on"
        output_mode = request.form.get("output", "pdf")  # pdf | epub | both

        # Advanced
        custom_width_pt = request.form.get("custom_width_pt")
        custom_height_pt = request.form.get("custom_height_pt")
        fit = request.form.get("fit", "contain")
        margin_top_pt = request.form.get("margin_top_pt")
        margin_right_pt = request.form.get("margin_right_pt")
        margin_bottom_pt = request.form.get("margin_bottom_pt")
        margin_left_pt = request.form.get("margin_left_pt")
        crop_threshold = clamp_int(request.form.get("crop_threshold"), 245, 0, 255)
        crop_pad = clamp_int(request.form.get("crop_pad"), 10, 0, 400)
        autocontrast_cutoff = clamp_int(request.form.get("autocontrast_cutoff"), 1, 0, 10)
        sharpen = request.form.get("sharpen") == "on"
        bilevel = request.form.get("bilevel") == "on"
        no_dither = request.form.get("no_dither") == "on"
        epub_bilevel = request.form.get("epub_bilevel") == "on"
        epub_no_dither = request.form.get("epub_no_dither") == "on"
        rotate_landscape = request.form.get("rotate_landscape") == "on"
        gs_quality = request.form.get("gs_quality", "prepress")
        force_gs = request.form.get("force_gs") == "on"
        force_raster = request.form.get("force_raster") == "on"

        # Optional custom output base name (without extension)
        output_name = request.form.get("output_name", "").strip()
        # Sanitize to a safe filename (keep words, digits, dashes, underscores, spaces -> dashes)
        def sanitize(name: str) -> str:
            name = name.strip().replace(" ", "-")
            name = re.sub(r"[^A-Za-z0-9._-]", "", name)
            return name[:128] or "output"

        if output_name:
            output_name = sanitize(output_name)

        with tempfile.TemporaryDirectory() as td:
            in_path = os.path.join(td, "input.pdf")
            out_pdf = os.path.join(td, "output.pdf")
            out_epub = os.path.join(td, "output.epub")
            file.save(in_path)

            pdf_bytes = None
            epub_bytes = None

            if output_mode in ("pdf", "both"):
                optimize_pdf(
                    in_pdf=in_path,
                    out_pdf=out_pdf,
                    page_size=page_size,
                    margin_pt=margin_pt,
                    margin_top_pt=clamp_int(margin_top_pt, margin_pt, 0, 400) if margin_top_pt else None,
                    margin_right_pt=clamp_int(margin_right_pt, margin_pt, 0, 400) if margin_right_pt else None,
                    margin_bottom_pt=clamp_int(margin_bottom_pt, margin_pt, 0, 400) if margin_bottom_pt else None,
                    margin_left_pt=clamp_int(margin_left_pt, margin_pt, 0, 400) if margin_left_pt else None,
                    custom_width_pt=clamp_int(custom_width_pt, 0, 100, 5000) if custom_width_pt else None,
                    custom_height_pt=clamp_int(custom_height_pt, 0, 100, 5000) if custom_height_pt else None,
                    dpi=dpi,
                    autocontrast=autocontrast,
                    autocontrast_cutoff=autocontrast_cutoff,
                    crop=crop,
                    crop_threshold=crop_threshold,
                    crop_pad=crop_pad,
                    fit_mode=fit,
                    sharpen=sharpen,
                    bilevel=bilevel,
                    dither=not no_dither,
                    rotate_landscape=rotate_landscape,
                    gs_quality=gs_quality,
                    force_gs=force_gs,
                    force_raster=force_raster,
                )
                with open(out_pdf, "rb") as f:
                    pdf_bytes = f.read()

            if output_mode in ("epub", "both"):
                pdf_to_epub(in_path, out_epub, epub_bilevel=epub_bilevel, epub_dither=not epub_no_dither)
                with open(out_epub, "rb") as f:
                    epub_bytes = f.read()

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        orig_base = os.path.splitext(file.filename)[0]
        base = output_name or orig_base

        if output_mode == "pdf":
            pdf_name = base if base.lower().endswith(".pdf") else f"{base}.pdf"
            return send_file(
                io.BytesIO(pdf_bytes or b""),
                mimetype="application/pdf",
                as_attachment=True,
                download_name=pdf_name,
            )
        if output_mode == "epub":
            epub_name = base if base.lower().endswith(".epub") else f"{base}.epub"
            return send_file(
                io.BytesIO(epub_bytes or b""),
                mimetype="application/epub+zip",
                as_attachment=True,
                download_name=epub_name,
            )
        # both: ZIP (and include individually named files inside)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            if pdf_bytes:
                inner_pdf = base if base.lower().endswith(".pdf") else f"{base}.pdf"
                zf.writestr(inner_pdf, pdf_bytes)
            if epub_bytes:
                inner_epub = base if base.lower().endswith(".epub") else f"{base}.epub"
                zf.writestr(inner_epub, epub_bytes)
        buf.seek(0)
        zip_name = f"{base}_converted_{stamp}.zip"
        return send_file(
            buf,
            mimetype="application/zip",
            as_attachment=True,
            download_name=zip_name,
        )

    return render_template("index.html", test_mode=TEST_MODE)


@app.route("/pricing", methods=["GET"]) 
def pricing():
    _ensure_csrf_token()
    # Show a styled pricing page with checkout link (or test-mode shortcut)
    if TEST_MODE:
        return render_template("pricing.html", test_mode=True, price_label="£2/month")
    if not (stripe and STRIPE_PRICE_ID and STRIPE_SECRET):
        return ("Payments not configured. Set STRIPE_SECRET_KEY and STRIPE_PRICE_ID env vars.", 503)
    return render_template("pricing.html", test_mode=False, price_label="£2/month")


@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    _require_csrf()
    if TEST_MODE:
        session["customer_id"] = "test_customer"
        try:
            set_subscription("test_customer", "test@example.com", "active", int(time.time()) + 3600 * 24 * 365 * 10)
        except Exception:
            pass
        return redirect(url_for("index"))
    if not (stripe and STRIPE_PRICE_ID and STRIPE_SECRET):
        flash("Payments not configured.", "error")
        return redirect(url_for("pricing"))
    try:
        checkout = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            success_url=f"{BASE_URL}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{BASE_URL}/pricing",
            automatic_tax={"enabled": True},
        )
        return redirect(checkout.url, code=303)
    except Exception as e:  # pragma: no cover
        flash(f"Checkout error: {e}", "error")
        return redirect(url_for("pricing"))


@app.route("/success")
def success():
    if not (stripe and STRIPE_SECRET):
        return redirect(url_for("pricing"))
    sess_id = request.args.get("session_id")
    if not sess_id:
        return redirect(url_for("pricing"))
    sess = stripe.checkout.Session.retrieve(sess_id, expand=["customer", "subscription"])
    customer = sess.get("customer")
    subscription = sess.get("subscription")
    if isinstance(customer, dict) and isinstance(subscription, dict):
        customer_id = customer.get("id")
        email = customer.get("email")
        status = subscription.get("status")
        period_end = subscription.get("current_period_end")
        if customer_id:
            set_subscription(customer_id, email, status, period_end)
            session["customer_id"] = customer_id
    return redirect(url_for("index"))


@app.route("/webhook", methods=["POST"])  # Stripe webhook to keep db in sync
def webhook():
    if TEST_MODE:
        return ("ok", 200)
    if not (stripe and STRIPE_WEBHOOK_SECRET):
        return ("not configured", 400)
    payload = request.get_data(as_text=True)
    sig = request.headers.get("Stripe-Signature", "")
    try:
        event = stripe.Webhook.construct_event(
            payload, sig, STRIPE_WEBHOOK_SECRET
        )
    except Exception:
        return ("invalid signature", 400)

    typ = event.get("type")
    data = event.get("data", {}).get("object", {})
    if typ in ("customer.subscription.updated", "customer.subscription.created"):
        sub = data
        customer_id = sub.get("customer")
        status = sub.get("status")
        period_end = sub.get("current_period_end")
        email = None
        if customer_id:
            set_subscription(customer_id, email, status or "", period_end)
    elif typ == "customer.subscription.deleted":
        sub = data
        customer_id = sub.get("customer")
        if customer_id:
            set_subscription(customer_id, None, "canceled", 0)
    return ("ok", 200)


@app.route("/test-activate", methods=["POST"])  # Manual test-mode activator
def test_activate():
    if not TEST_MODE:
        return redirect(url_for("pricing"))
    _require_csrf()
    session["customer_id"] = "test_customer"
    try:
        set_subscription("test_customer", "test@example.com", "active", int(time.time()) + 3600 * 24 * 365 * 10)
    except Exception:
        pass
    return redirect(url_for("index"))


def run(host: str = "127.0.0.1", port: int = 5000, debug: bool = False) -> None:
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    try:
        port = int(os.environ.get("PORT", "5000"))
    except ValueError:
        port = 5000
    run(host=host, port=port, debug=True)
