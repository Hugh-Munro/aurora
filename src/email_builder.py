"""
src/email_builder.py
--------------------
Assembles the final HTML and plain-text email and sends it via SMTP.
Public entry points:
  build_email(subject, portfolio_html, workout_plain, workout_html,
              weather_str, quote) -> tuple[str, str]  # (plain, html)
  send_email(cfg, subject, body_text, body_html) -> None
"""
from __future__ import annotations

import smtplib
from datetime import date
from email.message import EmailMessage
from html import escape as html_escape

from src.config import Config, GREEN
from src.quote import Quote
from src.weather import get_weather_icon


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
    msg = EmailMessage()
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


# =============================================================================
# BUILDERS
# =============================================================================

def _build_plain(
    subject:       str,
    workout_plain: str,
    pretty:        str,
    q:             Quote,
) -> str:
    lines: list[str] = [
        subject,
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
    portfolio_html: str,
    workout_html:   str,
    weather_str:    str,
    pretty:         str,
    q:              Quote,
) -> str:
    parts: list[str] = []

    # -- Outer wrapper --------------------------------------------------------
    parts.append(
        "<div style='max-width:600px; margin:0 auto; padding:1rem; "
        "font-family:Arial,sans-serif;'>"
    )

    # -- Header: title + weather ----------------------------------------------
    weather_icon = get_weather_icon(weather_str)
    weather_td   = (
        "<td style='vertical-align:bottom; text-align:right; width:140px;'>"
        f"<span style='font-size:22px; line-height:1; display:block;'>{weather_icon}</span>"
        f"<p style='font-size:12px; color:#555; margin:4px 0 0 0; white-space:nowrap;'>"
        f"{html_escape(weather_str.replace(' — ', ', '))}</p>"
        "</td>"
        if weather_str else ""
    )
    parts.append(
        "<table style='width:100%; border-collapse:collapse; margin-bottom:2rem;'><tr>"
        "<td style='vertical-align:bottom;'>"
        "<div style='border-left:3px solid #0F6E56; padding-left:1rem;'>"
        "<p style='font-size:12px; color:#888; margin:0 0 2px 0; "
        "letter-spacing:0.08em; text-transform:uppercase;'>Daily Update</p>"
        f"<h1 style='font-size:22px; font-weight:500; margin:0; color:#1a1a1a;'>"
        f"{html_escape(subject)}</h1>"
        "</div>"
        "</td>"
        f"{weather_td}"
        "</tr></table>"
    )

    # -- Portfolio ------------------------------------------------------------
    parts.append(portfolio_html)

    # -- Workout --------------------------------------------------------------
    parts.append(workout_html)

    # -- Quote ----------------------------------------------------------------
    attribution = (
        f"<p style='font-size:13px; color:#888; margin:0;'>"
        f"\u2014 {html_escape(q.author)}, <em>{html_escape(q.title)}</em></p>"
        if q.author else
        f"<p style='font-size:13px; color:#888; margin:0;'>"
        f"\u2014 <em>{html_escape(q.title)}</em></p>"
    )
    parts.append(
        "<div style='background:#ffffff; border:0.5px solid #e0e0e0; "
        "border-radius:12px; padding:1.25rem;'>"
        "<p style='font-size:11px; color:#888; margin:0 0 10px 0; "
        "letter-spacing:0.08em; text-transform:uppercase;'>Quote</p>"
        "<blockquote style='margin:0 0 10px 0; padding-left:14px; "
        f"border-left:2px solid {GREEN};'>"
        "<p style='font-family:Georgia,serif; font-size:15px; line-height:1.7; "
        f"margin:0; font-style:italic; color:#1a1a1a;'>{html_escape(pretty)}</p>"
        "</blockquote>"
        f"{attribution}"
        "</div>"
    )

    # -- Close wrapper --------------------------------------------------------
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
) -> tuple[str, str]:
    """Assemble the complete plain-text and HTML email body.

    Returns (body_text, body_html).
    """
    subject = _subject_line()
    pretty  = _prettify_quote(q.text)

    body_text = _build_plain(subject, workout_plain, pretty, q)
    body_html = _build_html(
        subject, portfolio_html, workout_html, weather_str, pretty, q
    )
    return subject, body_text, body_html