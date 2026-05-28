from __future__ import annotations
import csv
import os
import smtplib
import subprocess
import time
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from html import escape
from pathlib import Path

import requests
from dotenv import load_dotenv
from google import genai

load_dotenv()

CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
STRAVA_TOKEN_FILE = "strava_tokens.json"
PLAN_PATH = Path("data/training_plan.csv")
NOTES_PATH = Path("data/notes.txt")
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
MAIL_FROM = os.getenv("MAIL_FROM", "")
MAIL_TO = os.getenv("MAIL_TO", "")

DAY_NAMES = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}


# --- Strava ---

def load_tokens():
    import json
    refresh_token = os.getenv("STRAVA_REFRESH_TOKEN")
    if refresh_token:
        return {"access_token": None, "refresh_token": refresh_token, "expires_at": 0}
    with open(STRAVA_TOKEN_FILE) as f:
        return json.load(f)


def refresh_if_needed(tokens):
    import json
    if tokens["expires_at"] < time.time():
        response = requests.post("https://www.strava.com/oauth/token", data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": tokens["refresh_token"],
        })
        data = response.json()
        if "access_token" not in data:
            raise RuntimeError(f"Strava token refresh failed: {data}")
        tokens = data
        if not os.getenv("STRAVA_REFRESH_TOKEN"):
            with open(STRAVA_TOKEN_FILE, "w") as f:
                json.dump(tokens, f)
    return tokens


def get_strava_activities(access_token: str, days: int = 7) -> list[dict]:
    after = int((datetime.now() - timedelta(days=days)).timestamp())
    response = requests.get(
        "https://www.strava.com/api/v3/athlete/activities",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"after": after, "per_page": 50},
    )
    data = response.json()
    if not isinstance(data, list):
        print(f"Strava API error: {data}")
        return []
    activities = []
    for a in data:
        activities.append({
            "date": a["start_date_local"][:10],
            "type": a["type"],
            "distance_km": round(a["distance"] / 1000, 2),
            "duration_min": round(a["moving_time"] / 60, 1),
            "avg_hr": a.get("average_heartrate", "N/A"),
            "avg_pace": _format_pace(a.get("average_speed", 0)),
            "description": a.get("description", ""),
        })
    return activities


def _format_pace(speed_ms: float) -> str:
    if not speed_ms:
        return "N/A"
    spk = 1000 / speed_ms
    return f"{int(spk // 60)}:{int(spk % 60):02d}/km"


# --- Plan ---

def read_plan() -> list[dict]:
    with open(PLAN_PATH, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_plan(rows: list[dict]) -> None:
    if not rows:
        return
    with open(PLAN_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def parse_date(date_str: str) -> date | None:
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def get_week_plan(rows: list[dict], start: date, end: date) -> list[dict]:
    result = []
    for row in rows:
        d = parse_date(row["date"])
        if d and start <= d <= end:
            result.append(row)
    return result


# --- Notes ---

def read_notes() -> str:
    if not NOTES_PATH.exists():
        return "No notes."
    return NOTES_PATH.read_text(encoding="utf-8").strip() or "No notes."


# --- Helpers ---

def format_row_brief(row: dict) -> str:
    """For unchanged rows: just session name, plus distance for runs."""
    session_name = row.get("session_name", "").strip()
    dist = row.get("distance_km", "").strip()
    session_type = row.get("session_type", "").strip().lower()
    if dist and session_type == "run":
        try:
            return f"{session_name} · {int(round(float(dist)))}km"
        except ValueError:
            pass
    return session_name


def format_row_full(row: dict) -> str:
    """For modified rows: distance plus details."""
    parts = []
    dist = row.get("distance_km", "").strip()
    if dist:
        try:
            parts.append(f"{int(round(float(dist)))}km")
        except ValueError:
            parts.append(dist)
    details = row.get("details", "").strip().strip('"')
    if details:
        parts.append(details)
    return " · ".join(parts) if parts else ""


# --- Gemini ---

def build_prompt(
    strava_activities: list[dict],
    this_week_plan: list[dict],
    next_week_plan: list[dict],
    notes: str,
) -> str:
    strava_text = "STRAVA ACTIVITIES THIS WEEK:\n"
    if strava_activities:
        for a in strava_activities:
            strava_text += f"  {a['date']} | {a['type']} | {a['distance_km']}km | {a['duration_min']}min | HR: {a['avg_hr']} | Pace: {a['avg_pace']}\n"
            if a["description"]:
                strava_text += f"    Notes: {a['description']}\n"
    else:
        strava_text += "  No activities recorded.\n"

    plan_text = "PLANNED SESSIONS THIS WEEK:\n"
    for row in this_week_plan:
        plan_text += f"  {row['date']} | {row['session_type']} | {row['session_name']} | {row.get('details', '')}\n"

    next_week_text = "NEXT WEEK PLANNED SESSIONS (these are what you may modify):\n"
    for row in next_week_plan:
        next_week_text += (
            f"  date={row['date']} | week={row['week']} | day={row['day']} | "
            f"location={row['location']} | session_type={row['session_type']} | "
            f"session_name={row['session_name']} | details={row.get('details', '')} | "
            f"distance_km={row.get('distance_km', '')} | target_pace={row.get('target_pace', '')} | "
            f"target_hr_zone={row.get('target_hr_zone', '')} | sets_reps={row.get('sets_reps', '')}\n"
        )

    return f"""You are a conservative running and fitness coach reviewing an athlete's training week.

{strava_text}
{plan_text}
{next_week_text}

ATHLETE NOTES:
{notes}

RULES — follow these strictly:
- Only modify next week's sessions, never past dates
- Maximum distance change is 15% up or down
- Always use whole numbers for distances (e.g. 8km not 7.65km)
- You may swap session order within the week but not change session types
- You may substitute gym for bodyweight if location is waterford or holiday
- Do not increase intensity if this week was underperformed
- Do not add new sessions
- Keep all changes minimal and conservative
- Preserve the exact CSV field names and structure
- Use commas to separate exercises in the details field, never pipe characters or quotes

Respond with ONLY two sections, nothing else:

SUMMARY:
[3-5 sentences explaining what you changed and why, or confirming no changes were needed]

UPDATED_PLAN:
[The complete updated next week rows in exact CSV format with these headers:]
date,week,day,location,session_type,session_name,details,distance_km,target_pace,target_hr_zone,sets_reps

Do not include any other text, explanation, or markdown formatting outside these two sections.
"""


def parse_gemini_response(response_text: str) -> tuple[str, list[dict]]:
    summary = ""
    updated_rows = []

    if "SUMMARY:" in response_text:
        summary_part = response_text.split("SUMMARY:")[1]
        if "UPDATED_PLAN:" in summary_part:
            summary = summary_part.split("UPDATED_PLAN:")[0].strip()
        else:
            summary = summary_part.strip()

    if "UPDATED_PLAN:" in response_text:
        plan_part = response_text.split("UPDATED_PLAN:")[1].strip()
        lines = [ln.strip() for ln in plan_part.splitlines() if ln.strip()]
        if lines:
            headers = [h.strip() for h in lines[0].split(",")]
            for line in lines[1:]:
                values = line.split(",", len(headers) - 1)
                if len(values) == len(headers):
                    row = dict(zip(headers, values))
                    dist = row.get("distance_km", "").strip()
                    if dist:
                        try:
                            row["distance_km"] = str(int(round(float(dist))))
                        except ValueError:
                            pass
                    updated_rows.append(row)

    return summary, updated_rows


def find_true_changes(updated_rows: list[dict], original_rows: list[dict]) -> list[dict]:
    """Return only rows where meaningful content actually changed."""
    original_lookup = {r["date"]: r for r in original_rows}
    IGNORE_FIELDS = {"sets_reps"}
    changed = []
    for row in updated_rows:
        orig = original_lookup.get(row["date"])
        if not orig:
            changed.append(row)
            continue
        for key, val in row.items():
            if key in IGNORE_FIELDS:
                continue
            orig_val = orig.get(key, "").strip()
            new_val = val.strip()
            if orig_val != new_val:
                changed.append(row)
                break
    return changed


# --- Git ---

def git_commit_and_push(message: str) -> None:
    try:
        subprocess.run(["git", "config", "user.name", "github-actions"], check=True)
        subprocess.run(["git", "config", "user.email", "github-actions@github.com"], check=True)
        subprocess.run(["git", "add", "data/training_plan.csv"], check=True)
        result = subprocess.run(["git", "diff", "--cached", "--quiet"])
        if result.returncode == 0:
            print("No changes to commit.")
            return
        subprocess.run(["git", "commit", "-m", message], check=True)
        subprocess.run(["git", "push"], check=True)
        print("Plan committed and pushed.")
    except subprocess.CalledProcessError as e:
        print(f"Git error: {e}")


# --- Email ---

def send_review_email(
    summary: str,
    updated_rows: list[dict],
    final_next_week: list[dict],
    original_next_week: list[dict],
) -> None:
    today_str = date.today().strftime("%a %d %b %Y")
    subject = f"Weekly Training Review: {today_str}"

    original_lookup = {r["date"]: r for r in original_next_week}
    changed_dates = {r["date"] for r in updated_rows}

    # Plain text
    plain = f"Weekly Training Review\n\n{summary}\n\nNext week:\n"
    for row in final_next_week:
        d = parse_date(row["date"])
        day_name = DAY_NAMES.get(d.weekday(), "") if d else ""
        modified = row["date"] in changed_dates
        prefix = "[MODIFIED] " if modified else ""
        plain += f"  {prefix}{day_name} {row['date']} | {format_row_brief(row)}\n"

    # HTML rows
    rows_html = ""
    for row in final_next_week:
        d = parse_date(row["date"])
        day_name = DAY_NAMES.get(d.weekday(), "") if d else ""
        try:
            date_num = d.strftime("%-d %b") if d else row["date"]
        except ValueError:
            date_num = d.strftime("%d %b").lstrip("0") if d else row["date"]

        modified = row["date"] in changed_dates
        orig = original_lookup.get(row["date"])

        if modified:
            details = format_row_full(row)
            orig_details = format_row_full(orig) if orig else ""
            strikethrough = (
                f"<p style='font-family:Arial,sans-serif;font-size:11px;color:#888888;"
                f"margin:0 0 3px 0;text-decoration:line-through;'>{escape(orig_details)}</p>"
                if orig_details and orig_details != details else ""
            )
            rows_html += (
                f"<tr>"
                f"<td style='padding:6px 10px 6px 0;vertical-align:top;width:44px;text-align:center;'>"
                f"<p style='font-family:Arial,sans-serif;font-size:11px;font-weight:bold;color:#0F6E56;margin:0;'>{day_name}</p>"
                f"<p style='font-family:Arial,sans-serif;font-size:10px;color:#0F6E56;margin:0;'>{date_num}</p>"
                f"</td>"
                f"<td style='padding:6px 0;'>"
                f"<div style='padding:10px 12px;background:#E1F5EE;border-radius:8px;'>"
                f"<table role='presentation' cellpadding='0' cellspacing='0' border='0' style='width:100%;border-collapse:collapse;margin-bottom:4px;'>"
                f"<tr>"
                f"<td style='font-family:Arial,sans-serif;font-size:12px;font-weight:bold;color:#085041;'>{escape(row['session_name'])}</td>"
                f"<td style='text-align:right;'><span style='font-family:Arial,sans-serif;font-size:10px;color:#0F6E56;"
                f"background:#ffffff;border:0.5px solid #0F6E56;padding:2px 7px;border-radius:20px;'>&#10022; modified</span></td>"
                f"</tr>"
                f"</table>"
                f"{strikethrough}"
                f"<p style='font-family:Arial,sans-serif;font-size:11px;color:#085041;margin:0;'>{escape(details)}</p>"
                f"</div>"
                f"</td>"
                f"</tr>"
                f"<tr><td colspan='2' style='height:6px;'></td></tr>"
            )
        else:
            rows_html += (
                f"<tr>"
                f"<td style='padding:6px 10px 6px 0;vertical-align:top;width:44px;text-align:center;'>"
                f"<p style='font-family:Arial,sans-serif;font-size:11px;font-weight:bold;color:#1a1a1a;margin:0;'>{day_name}</p>"
                f"<p style='font-family:Arial,sans-serif;font-size:10px;color:#888888;margin:0;'>{date_num}</p>"
                f"</td>"
                f"<td style='padding:6px 0;'>"
                f"<div style='padding:10px 12px;background:#f7f7f5;border-radius:8px;'>"
                f"<p style='font-family:Arial,sans-serif;font-size:12px;font-weight:bold;color:#1a1a1a;margin:0;'>{escape(format_row_brief(row))}</p>"
                f"</div>"
                f"</td>"
                f"</tr>"
                f"<tr><td colspan='2' style='height:6px;'></td></tr>"
            )

    html = (
        "<div style='max-width:600px;margin:0 auto;padding:1rem;font-family:Arial,sans-serif;'>"
        "<div style='border-left:3px solid #0F6E56;padding-left:1rem;margin-bottom:2rem;'>"
        "<p style='font-size:12px;color:#888;margin:0 0 2px 0;letter-spacing:0.08em;text-transform:uppercase;'>Weekly Review</p>"
        f"<h1 style='font-size:22px;font-weight:500;margin:0;color:#1a1a1a;'>{escape(today_str)}</h1>"
        "</div>"
        "<div style='background:#ffffff;border:1px solid #e0e0e0;border-radius:12px;padding:20px;margin-bottom:16px;'>"
        "<p style='font-size:11px;color:#888;margin:0 0 10px 0;letter-spacing:0.08em;text-transform:uppercase;'>Coach Summary</p>"
        f"<p style='font-size:14px;color:#1a1a1a;line-height:1.7;margin:0;'>{escape(summary)}</p>"
        "</div>"
        "<div style='background:#ffffff;border:1px solid #e0e0e0;border-radius:12px;padding:20px;'>"
        "<p style='font-size:11px;color:#888;margin:0 0 14px 0;letter-spacing:0.08em;text-transform:uppercase;'>Next week</p>"
        f"<table role='presentation' cellpadding='0' cellspacing='0' border='0' style='width:100%;border-collapse:collapse;'>"
        f"{rows_html}"
        "</table>"
        "</div>"
        "</div>"
    )

    msg = EmailMessage()
    msg["From"] = MAIL_FROM
    msg["To"] = MAIL_TO
    msg["Subject"] = subject
    msg.set_content(plain)
    msg.add_alternative(html, subtype="html")

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as s:
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)
    print("Review email sent.")


# --- Main ---

def main() -> None:
    print("Starting weekly review...")

    # Strava
    tokens = load_tokens()
    tokens = refresh_if_needed(tokens)
    activities = get_strava_activities(tokens["access_token"], days=7)
    print(f"Fetched {len(activities)} Strava activities.")

    # Plan
    all_rows = read_plan()
    today = date.today()
    week_start = today - timedelta(days=today.weekday() + 1)
    week_end = today
    next_week_start = today + timedelta(days=1)
    next_week_end = today + timedelta(days=7)

    this_week = get_week_plan(all_rows, week_start, week_end)
    next_week = get_week_plan(all_rows, next_week_start, next_week_end)

    if not next_week:
        print("No next week plan found. Exiting.")
        return

    # Capture originals before any modification
    original_next_week = [dict(r) for r in next_week]

    # Notes
    notes = read_notes()

    # Gemini
    print("Sending to Gemini...")
    prompt = build_prompt(activities, this_week, next_week, notes)
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    summary, updated_rows = parse_gemini_response(response.text)
    updated_rows = find_true_changes(updated_rows, original_next_week)
    print(f"Summary: {summary}")
    print(f"Updated rows: {len(updated_rows)}")

    # Update plan
    if updated_rows:
        updated_dates = {row["date"] for row in updated_rows}
        new_plan = []
        for row in all_rows:
            if row["date"] in updated_dates:
                matching = next((r for r in updated_rows if r["date"] == row["date"]), None)
                new_plan.append(matching if matching else row)
            else:
                new_plan.append(row)
        write_plan(new_plan)
        print("Plan updated.")
        final_next_week = get_week_plan(new_plan, next_week_start, next_week_end)
        git_commit_and_push(f"Weekly review update {today.isoformat()}")
    else:
        print("No plan changes.")
        final_next_week = next_week
        original_next_week = next_week

    # Email
    send_review_email(summary, updated_rows, final_next_week, original_next_week)


if __name__ == "__main__":
    main()  