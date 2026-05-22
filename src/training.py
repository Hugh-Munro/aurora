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
    if row is None:
        plain = "No session planned for today."
        html = "<p style='color: var(--color-text-secondary); font-size: 14px;'>No session planned for today.</p>"
        return plain, html

    session_type = row.get("session_type", "").lower()
    session_name = row.get("session_name", "")
    details = row.get("details", "")
    location = row.get("location", "").capitalize()

    PILL_STYLES = {
        "run": ("background:#E1F5EE; color:#0F6E56;", "RUN"),
        "gym": ("background:#F1EFE8; color:#444441;", "GYM"),
        "bodyweight": ("background:#FAEEDA; color:#633806;", "BODYWEIGHT"),
        "rest": ("background:#D3D1C7; color:#2C2C2A;", "REST"),
    }
    pill_style, pill_label = PILL_STYLES.get(session_type, ("background:#F1EFE8; color:#444441;", session_type.upper()))

    pill_html = (
        f"<span style='font-size:11px; font-weight:500; padding:3px 10px; "
        f"border-radius:20px; letter-spacing:0.04em; {pill_style}'>{pill_label}</span>"
    )

    header_html = f"""
<div style='display:flex; align-items:center; gap:10px; margin-bottom:1rem;'>
  {pill_html}
  <h2 style='font-size:16px; font-weight:500; margin:0; color:var(--color-text-primary);'>{session_name}</h2>
  <span style='font-size:13px; color:var(--color-text-tertiary); margin-left:auto;'>{location}</span>
</div>"""

    card_open = "<div style='background:var(--color-background-primary); border:0.5px solid var(--color-border-tertiary); border-radius:12px; padding:1.25rem; margin-bottom:1rem;'>"
    card_close = "</div>"

    if session_type == "run":
        distance = row.get("distance_km", "")
        pace = row.get("target_pace", "")
        hr_zone = row.get("target_hr_zone", "")

        def metric_card(label, value):
            return f"""
<div style='background:var(--color-background-secondary); border-radius:8px; padding:10px 12px;'>
  <p style='font-size:11px; color:var(--color-text-tertiary); margin:0 0 2px 0; letter-spacing:0.04em;'>{label}</p>
  <p style='font-size:18px; font-weight:500; margin:0; color:var(--color-text-primary);'>{value}</p>
</div>"""

        metrics_html = f"""
<div style='display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin-bottom:1rem;'>
  {metric_card("DISTANCE", f"{distance} km") if distance else ""}
  {metric_card("TARGET PACE", pace) if pace else ""}
  {metric_card("HR ZONE", hr_zone) if hr_zone else ""}
</div>"""

        notes_html = f"<p style='font-size:13px; color:var(--color-text-secondary); margin:0; border-left:2px solid var(--color-border-tertiary); padding-left:10px;'>{details}</p>" if details else ""

        body_html = metrics_html + notes_html
        plain = f"{session_name} ({location})\nDistance: {distance}km | Pace: {pace} | Zone: {hr_zone}\n{details}"

    elif session_type in ("gym", "bodyweight"):
        exercises = [e.strip() for e in details.split(",") if e.strip()]
        rows_html = ""
        plain_lines = [f"{session_name} ({location})"]
        for ex in exercises:
            parts = ex.rsplit("@", 1)
            if len(parts) == 2:
                name_sets = parts[0].strip()
                weight = "@ " + parts[1].strip()
            else:
                name_sets = ex
                weight = ""
            set_split = name_sets.rsplit(" ", 1)
            if len(set_split) == 2 and "x" in set_split[1].lower():
                ex_name = set_split[0]
                sets_reps = set_split[1]
            else:
                ex_name = name_sets
                sets_reps = ""
            display_right = f"{sets_reps} {weight}".strip()
            rows_html += f"""
<div style='display:flex; justify-content:space-between; align-items:center; padding:8px 10px; background:var(--color-background-secondary); border-radius:8px;'>
  <span style='font-size:13px; color:var(--color-text-primary);'>{ex_name}</span>
  <span style='font-size:13px; color:var(--color-text-secondary); font-weight:500;'>{display_right}</span>
</div>"""
            plain_lines.append(f"  {ex_name} {display_right}")

        body_html = f"<div style='display:flex; flex-direction:column; gap:6px;'>{rows_html}</div>"
        plain = "\n".join(plain_lines)

    else:
        body_html = f"<p style='font-size:13px; color:var(--color-text-secondary); margin:0;'>{details}</p>" if details else ""
        plain = f"{session_name} ({location})\n{details}"

    html = card_open + header_html + body_html + card_close
    return plain, html