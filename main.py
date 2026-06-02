"""
main.py
-------
Entry point for the AURORA daily email system.
Orchestrates the data pipeline and delegates to src modules.
"""
from __future__ import annotations

from src.config import (
    load_config,
    PASSAGES_FOLDER,
    PDF_PATTERN,
    RECURSIVE,
    GAP_MULTIPLIER,
)
from src.weather import get_weather
from src.quote import pick_random_quote
from src.training import get_today_plan, format_plan_for_email
from src.portfolio import build_portfolio_html
from src.email_builder import build_email, send_email


def main() -> int:
    # -- Config ---------------------------------------------------------------
    cfg = load_config()

    # -- Data -----------------------------------------------------------------
    plan_row       = get_today_plan()
    location       = (plan_row.get("location", "dublin") if plan_row else "dublin")
    weather_str    = get_weather(location)
    workout_plain, workout_html = format_plan_for_email(plan_row)
    portfolio_html = build_portfolio_html()
    q              = pick_random_quote(
        PASSAGES_FOLDER,
        pattern=PDF_PATTERN,
        recursive=RECURSIVE,
        gap_multiplier=GAP_MULTIPLIER,
    )

    # -- Build + send ---------------------------------------------------------
    subject, body_text, body_html = build_email(
        portfolio_html=portfolio_html,
        workout_plain=workout_plain,
        workout_html=workout_html,
        weather_str=weather_str,
        q=q,
    )
    send_email(cfg, subject, body_text, body_html)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())