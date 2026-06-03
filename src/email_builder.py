"""
src/email_builder.py
--------------------
Assembles the final HTML and plain-text email and sends it via SMTP.
Public entry points:
  build_email(portfolio_html, workout_plain, workout_html, weather_str, quote) -> tuple[str, str, str]
  send_email(cfg, subject, body_text, body_html) -> None
"""
from __future__ import annotations

import os
import random
import smtplib
from datetime import date
from email.message import EmailMessage
from html import escape as html_escape

from src.config import Config, GREEN
from src.quote import Quote
from src.weather import get_weather_icon


# =============================================================================
# FALLBACK GREETINGS
# =============================================================================

GREETINGS = [
    "Good morning.",
    "Good morning, Hugh.",
    "Morning.",
    "Morning, Hugh.",
    "Another day.",
    "Another day, Hugh.",
    "Good morning. Let's go.",
    "Morning, Hugh. Let's go.",
    "Good morning. Here we go.",
    "Morning. Make it count.",
    "Good morning, Hugh. Make it count.",
    "Rise and shine, Hugh.",
    "Good morning. Let's get to it.",
    "Morning, Hugh. Let's get to it.",
    "Good morning, Hugh. Another one.",
]

def _get_greeting() -> str:
    return random.choice(GREETINGS)

# =============================================================================
# SMTP
# =============================================================================

def send_email(
    cfg:       Config,
    subject:   str,
    body_text: str,
    body_html: str,
) -> None:
    """Send a plain+HTML multipart email via SMTP."""
    msg            = EmailMessage()
    msg["From"]    = cfg.mail_from
    msg["To"]      = cfg.mail_to
    msg["Subject"] = subject
    msg.set_content(body_text)
    msg.add_alternative(body_html, subtype="html")

    if cfg.smtp_port == 465:
        with smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port) as s:
            s.login(cfg.smtp_user, cfg.smtp_pass)
            s.send_message(msg)
    else:
        with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port) as s:
            s.ehlo()
            s.starttls()
            s.login(cfg.smtp_user, cfg.smtp_pass)
            s.send_message(msg)


# =============================================================================
# HELPERS
# =============================================================================

def _prettify_quote(text: str) -> str:
    lines = [ln.lstrip().lstrip("> ").rstrip() for ln in text.splitlines()]
    return "\n".join(lines).strip()


def _subject_line() -> str:
    return f"Daily Update: {date.today().strftime('%a %d %b %Y')}"


today = date.today()

# =============================================================================
# BUILDERS
# =============================================================================

def _build_plain(
    subject:       str,
    greeting:      str,
    workout_plain: str,
    pretty:        str,
    q:             Quote,
) -> str:
    lines: list[str] = [
        subject,
        "",
        greeting,
        "",
        "Portfolio",
        "See HTML version for portfolio details.",
        "",
        "Workout",
        workout_plain,
        "",
        "Quote",
        f"\u201c{pretty}\u201d",
        f"\u2014 {q.author}, {q.title}" if q.author else f"\u2014 {q.title}",
    ]
    return "\n".join(lines)


def _build_html(
    subject:        str,
    greeting:       str,
    portfolio_html: str,
    workout_html:   str,
    weather_str:    str,
    pretty:         str,
    q:              Quote,
) -> str:
    parts: list[str] = []

    parts.append(
        "<div style='max-width:600px; margin:0 auto; padding:1rem; "
        "font-family:Arial,sans-serif; background:#e8e7e3; border-radius:16px;'>"
    )

    # -- Header ---------------------------------------------------------------
    weather_icon = get_weather_icon(weather_str)
    weather_right = ""
    if weather_str:
        # Split "Heavy drizzle — 14–18°C, 1.0mm rain" into description and detail
        parts_w      = weather_str.split(" — ", 1)
        weather_desc = parts_w[0].strip()
        weather_detail = parts_w[1].strip() if len(parts_w) > 1 else ""
        weather_right = (
            "<td style='vertical-align:bottom; text-align:right; width:120px;'>"
            f"<p style='font-size:20px; line-height:1; margin:0;'>{weather_icon}</p>"
            f"<p style='font-size:12px; font-weight:500; color:#1a1a1a; margin:4px 0 0 0;'>"
            f"{html_escape(weather_desc)}</p>"
            + (
                f"<p style='font-size:11px; color:#555; margin:2px 0 0 0;'>"
                f"{html_escape(weather_detail)}</p>"
                if weather_detail else ""
            )
            + "</td>"
        )

    parts.append(
            "<div style='background:linear-gradient(180deg,#ffffff 0%,#edecea 100%);border-radius:12px;padding:1.5rem;margin-bottom:12px;"
            "box-shadow:0 2px 4px rgba(0,0,0,0.06),0 8px 20px rgba(0,0,0,0.08);'>"
            "<table style='width:100%; border-collapse:collapse;'><tr>"
            "<td style='vertical-align:bottom;'>"
            f"<p style='font-size:11px; color:#888; margin:0 0 6px 0;'>"
            f"{today.strftime('%A')}, {today.day} {today.strftime('%B %Y')}</p>"
            f"<p style='font-size:22px; font-weight:700; color:#1a1a1a !important; "
            f"line-height:1.25; margin:0;'>{html_escape(greeting)}</p>"
            "</td>"
            f"{weather_right}"
            "</tr></table>"
            "</div>"
        )

    # -- Portfolio ------------------------------------------------------------
    parts.append(portfolio_html)

    # -- Workout --------------------------------------------------------------
    parts.append(workout_html)

    # -- Quote ----------------------------------------------------------------
    attribution = (
        f"<p style='font-size:12px; color:#888; margin:0;'>"
        f"\u2014 {html_escape(q.author)}, <em>{html_escape(q.title)}</em></p>"
        if q.author else
        f"<p style='font-size:12px; color:#888; margin:0;'>"
        f"\u2014 <em>{html_escape(q.title)}</em></p>"
    )
    
    parts.append(
            "<div style='background:linear-gradient(180deg,#ffffff 0%,#edecea 100%);border-radius:12px;padding:1.25rem 1.5rem;"
            "box-shadow:0 2px 4px rgba(0,0,0,0.06),0 8px 20px rgba(0,0,0,0.08);'>"
            "<div style='height:30px;overflow:hidden;margin-bottom:10px;'>"
            f"<p style='font-family:Georgia,serif;font-size:48px;line-height:1;"
            f"color:{GREEN};margin:0;'>&ldquo;</p>"
            "</div>"
            "<p style='font-family:Georgia,serif; font-size:15px; line-height:1.75; "
            f"font-style:italic; color:#1a1a1a !important; margin:0 0 14px 0;'>{html_escape(pretty)}</p>"
            f"{attribution}"
            "</div>"
        )

    parts.append(
        "<div style='padding:2rem 0 0.5rem;text-align:center;'>"
        "<div style='width:5px;height:5px;border-radius:50%;background:#0F6E56;"
        "margin:0 auto 6px;'></div>"
        "<p style='font-family:Arial,sans-serif;font-size:11px;color:#888;"
        "letter-spacing:0.1em;'>Aurora</p>"
        "</div>"
    )

    parts.append("</div>")

    return "\n".join(parts)


# =============================================================================
# PUBLIC ENTRY POINT
# =============================================================================

def build_email(
    portfolio_html: str,
    workout_plain:  str,
    workout_html:   str,
    weather_str:    str,
    q:              Quote,
    plan_row:       dict | None = None,
) -> tuple[str, str, str]:
    """Assemble the complete plain-text and HTML email body.

    Returns (subject, body_text, body_html).
    """
    subject = _subject_line()
    pretty  = _prettify_quote(q.text)

    today   = date.today()
    day     = today.strftime("%A")
    session = (
        f"{plan_row.get('session_type', '')} — {plan_row.get('session_name', '')}"
        if plan_row else "unspecified"
    )

    greeting  = _get_greeting()
    body_text = _build_plain(subject, greeting, workout_plain, pretty, q)
    body_html = _build_html(
        subject, greeting, portfolio_html, workout_html, weather_str, pretty, q
    )
    return subject, body_text, body_html