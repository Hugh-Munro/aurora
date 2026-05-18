from __future__ import annotations

import os
import smtplib
from datetime import date
from email.message import EmailMessage
from html import escape as html_escape
from pathlib import Path

import monthly_recap


# ============================================================
# ENV LOADING
# ============================================================

def load_dotenv(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return
    for line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


# ============================================================
# EMAIL SENDER
# ============================================================

def send_email_smtp(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_pass: str,
    mail_from: str,
    mail_to: str,
    subject: str,
    body_text: str,
    body_html: str,
) -> None:
    msg = EmailMessage()
    msg["From"] = mail_from
    msg["To"] = mail_to
    msg["Subject"] = subject

    msg.set_content(body_text)
    msg.add_alternative(body_html, subtype="html")

    if smtp_port == 465:
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as s:
            s.login(smtp_user, smtp_pass)
            s.send_message(msg)
    else:
        with smtplib.SMTP(smtp_host, smtp_port) as s:
            s.ehlo()
            s.starttls()
            s.login(smtp_user, smtp_pass)
            s.send_message(msg)


# ============================================================
# DATE HELPERS
# ============================================================

def previous_month(today: date) -> tuple[int, int]:
    if today.month == 1:
        return today.year - 1, 12
    return today.year, today.month - 1


# ============================================================
# MAIN
# ============================================================

def main() -> int:
    today = date.today()
    year, month = previous_month(today)
    month_name = date(year, month, 1).strftime("%B %Y")

    # ---- LOAD ENV ----
    here = Path(__file__).resolve().parent
    load_dotenv(here / ".env")

    smtp_host = os.environ.get("SMTP_HOST", "")
    smtp_port = int(os.environ.get("SMTP_PORT", "465"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")
    mail_from = os.environ.get("MAIL_FROM", smtp_user)
    mail_to = os.environ.get("MAIL_TO", "")

    missing = [
        k
        for k in ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS", "MAIL_FROM", "MAIL_TO"]
        if not os.environ.get(k)
    ]
    if missing:
        raise SystemExit(f"Missing settings in .env: {', '.join(missing)}")

    # ========================================================
    # DATA
    # ========================================================

    task_pct = monthly_recap.calculate_monthly_completion(year, month)
    w0, w1, wd = monthly_recap.get_monthly_weight_change(year, month)
    pnl = monthly_recap.get_monthly_portfolio_pnl(year, month)

    study_hours = monthly_recap.get_monthly_study_hours(year, month)

    gym_sessions, kg_lifted = monthly_recap.get_monthly_workouts(year, month)
    runs, km_run = monthly_recap.get_monthly_running(year, month)

    books = monthly_recap.get_books_read_in_month(year, month)
    movies = monthly_recap.get_movies_watched_in_month(year, month)
    songs = monthly_recap.get_liked_songs_added_in_month(year, month)

    subject = f"Monthly Recap — {month_name}"

    # ========================================================
    # PLAIN TEXT
    # ========================================================

    lines: list[str] = []
    lines.append(subject)
    lines.append("")

    lines.append("CORE")
    lines.append(f"• Study hours: {study_hours:.1f} h")
    lines.append(f"• Task completion: {task_pct:.2f}%")
    lines.append(
        "• Portfolio PnL: insufficient data"
        if pnl is None
        else f"• Portfolio PnL: €{pnl:,.2f}"
    )
    lines.append("")

    lines.append("FITNESS")
    lines.append(f"• Runs: {runs} ({km_run:.2f} km)")
    lines.append(f"• Gym sessions: {gym_sessions} ({kg_lifted:,.0f} kg)")
    lines.append(
        "• Weight: insufficient data"
        if wd is None
        else f"• Weight: {w1:.1f} kg ({wd:+.1f} kg)"
    )
    lines.append("")

    lines.append("ARTS")
    lines.append(f"• Books read: {books}")
    lines.append(f"• Movies watched: {movies}")
    lines.append(f"• New liked songs: {songs}")

    body_text = "\n".join(lines)

    # ========================================================
    # HTML
    # ========================================================

    def section(title: str, items: list[str]) -> str:
        out = [
            f"<h3 style='margin-top:22px; margin-bottom:6px;'>"
            f"{html_escape(title)}</h3>",
            "<ul style='margin-top:0;'>",
        ]
        out += [f"<li>{html_escape(i)}</li>" for i in items]
        out.append("</ul>")
        return "\n".join(out)

    html_parts = [
        "<div style='font-family:Segoe UI, Arial, sans-serif;'>",
        f"<h1>{html_escape(subject)}</h1>",
        section(
            "CORE",
            [
                f"Study hours: {study_hours:.1f} h",
                f"Task completion: {task_pct:.2f}%",
                "Portfolio PnL: insufficient data"
                if pnl is None
                else f"Portfolio PnL: €{pnl:,.2f}",
            ],
        ),
        section(
            "FITNESS",
            [
                f"Runs: {runs} ({km_run:.2f} km)",
                f"Gym sessions: {gym_sessions} ({kg_lifted:,.0f} kg)",
                "Weight: insufficient data"
                if wd is None
                else f"Weight: {w1:.1f} kg ({wd:+.1f} kg)",
            ],
        ),
        section(
            "ARTS",
            [
                f"Books read: {books}",
                f"Movies watched: {movies}",
                f"New liked songs: {songs}",
            ],
        ),
        "</div>",
    ]

    body_html = "\n".join(html_parts)

    # ========================================================
    # SEND
    # ========================================================

    send_email_smtp(
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_user=smtp_user,
        smtp_pass=smtp_pass,
        mail_from=mail_from,
        mail_to=mail_to,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
