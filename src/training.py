from __future__ import annotations

import csv
from datetime import date
from pathlib import Path


PLAN_PATH = Path(__file__).resolve().parent.parent / "data" / "training_plan.csv"


def get_today_plan(plan_path: Path = PLAN_PATH) -> dict | None:
    today = date.today().isoformat()
    with open(plan_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["date"] == today:
                return row
    return None


def format_plan_for_email(row: dict | None) -> tuple[str, str]:
    """Returns (plain_text, html) for today's session."""

    if row is None:
        return "No session planned for today.", "<p>No session planned for today.</p>"

    session_type = row.get("session_type", "").lower()
    session_name = row.get("session_name", "")
    details = row.get("details", "")
    location = row.get("location", "").capitalize()

    # --- Plain text ---
    lines = [f"{session_name} ({location})"]

    if session_type == "run":
        distance = row.get("distance_km", "")
        pace = row.get("target_pace", "")
        hr_zone = row.get("target_hr_zone", "")
        if distance:
            lines.append(f"Distance: {distance} km")
        if pace:
            lines.append(f"Target pace: {pace}")
        if hr_zone:
            lines.append(f"HR zone: {hr_zone}")
        if details:
            lines.append(f"Session: {details}")

    elif session_type in ("gym", "bodyweight"):
        if details:
            exercises = details.split(",")
            for ex in exercises:
                lines.append(f"• {ex.strip()}")

    elif session_type == "rest":
        if details:
            lines.append(details)

    plain = "\n".join(lines)

    # --- HTML ---
    html_lines = [
        f"<h3 style='margin:0 0 8px 0;'>{session_name} "
        f"<span style='font-weight:normal; color:#666;'>({location})</span></h3>"
    ]

    if session_type == "run":
        distance = row.get("distance_km", "")
        pace = row.get("target_pace", "")
        hr_zone = row.get("target_hr_zone", "")
        html_lines.append("<ul style='margin:0; padding-left:20px;'>")
        if distance:
            html_lines.append(f"<li>Distance: {distance} km</li>")
        if pace:
            html_lines.append(f"<li>Target pace: {pace}</li>")
        if hr_zone:
            html_lines.append(f"<li>HR zone: {hr_zone}</li>")
        if details:
            html_lines.append(f"<li>Session: {details}</li>")
        html_lines.append("</ul>")

    elif session_type in ("gym", "bodyweight"):
        if details:
            html_lines.append("<ul style='margin:0; padding-left:20px;'>")
            for ex in details.split(","):
                html_lines.append(f"<li>{ex.strip()}</li>")
            html_lines.append("</ul>")

    elif session_type == "rest":
        if details:
            html_lines.append(f"<p style='margin:4px 0;'>{details}</p>")

    html = "\n".join(html_lines)
    return plain, html