from __future__ import annotations

import csv
import os
import subprocess
import time
from datetime import date, datetime, timedelta
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
        tokens = response.json()
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
    activities = []
    for a in response.json():
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


def get_week_plan(rows: list[dict], start: date, end: date) -> list[dict]:
    result = []
    for row in rows:
        try:
            d = datetime.strptime(row["date"], "%d/%m/%Y").date()
        except ValueError:
            try:
                d = datetime.strptime(row["date"], "%Y-%m-%d").date()
            except ValueError:
                continue
        if start <= d <= end:
            result.append(row)
    return result


# --- Notes ---

def read_notes() -> str:
    if not NOTES_PATH.exists():
        return "No notes."
    return NOTES_PATH.read_text(encoding="utf-8").strip() or "No notes."


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

    prompt = f"""You are a conservative running and fitness coach reviewing an athlete's training week.

{strava_text}
{plan_text}
{next_week_text}

ATHLETE NOTES:
{notes}

RULES — follow these strictly:
- Only modify next week's sessions, never past dates
- Maximum distance change is 15% up or down
- You may swap session order within the week but not change session types
- You may substitute gym for bodyweight if location is waterford or holiday
- Do not increase intensity if this week was underperformed
- Do not add new sessions
- Keep all changes minimal and conservative
- Preserve the exact CSV field names and structure

Respond with ONLY two sections, nothing else:

SUMMARY:
[3-5 sentences explaining what you changed and why, or confirming no changes were needed]

UPDATED_PLAN:
[The complete updated next week rows in exact CSV format with these headers:]
date,week,day,location,session_type,session_name,details,distance_km,target_pace,target_hr_zone,sets_reps

Do not include any other text, explanation, or markdown formatting outside these two sections.
"""
    return prompt


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
        lines = [l.strip() for l in plan_part.splitlines() if l.strip()]
        if lines:
            headers = [h.strip() for h in lines[0].split(",")]
            for line in lines[1:]:
                values = line.split(",", len(headers) - 1)
                if len(values) == len(headers):
                    updated_rows.append(dict(zip(headers, values)))

    return summary, updated_rows


# --- Git ---

def git_commit_and_push(message: str) -> None:
    try:
        subprocess.run(["git", "add", "data/training_plan.csv"], check=True)
        subprocess.run(["git", "commit", "-m", message], check=True)
        subprocess.run(["git", "push"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Git error: {e}")


# --- Email ---

def send_review_email(summary: str, changes: list[dict]) -> None:
    import smtplib
    from email.message import EmailMessage
    from html import escape

    today_str = date.today().strftime("%a %d %b %Y")
    subject = f"Weekly Training Review: {today_str}"

    # Plain text
    plain = f"Weekly Training Review\n\n{summary}\n"
    if changes:
        plain += "\nChanges made to next week:\n"
        for row in changes:
            plain += f"  {row['date']} | {row['session_name']} | {row.get('details', '')}\n"
    else:
        plain += "\nNo changes made to next week's plan."

    # HTML
    html = (
        "<div style='max-width:600px; margin:0 auto; padding:1rem; font-family:Arial,sans-serif;'>"
        "<div style='border-left:3px solid #0F6E56; padding-left:1rem; margin-bottom:2rem;'>"
        "<p style='font-size:12px; color:#888; margin:0 0 2px 0; letter-spacing:0.08em; text-transform:uppercase;'>Weekly Review</p>"
        f"<h1 style='font-size:22px; font-weight:500; margin:0; color:#1a1a1a;'>{escape(today_str)}</h1>"
        "</div>"
        "<div style='background:#ffffff; border:1px solid #e0e0e0; border-radius:12px; padding:20px; margin-bottom:16px;'>"
        "<p style='font-size:11px; color:#888; margin:0 0 10px 0; letter-spacing:0.08em; text-transform:uppercase;'>Coach Summary</p>"
        f"<p style='font-size:14px; color:#1a1a1a; line-height:1.7; margin:0;'>{escape(summary)}</p>"
        "</div>"
    )

    if changes:
        html += (
            "<div style='background:#ffffff; border:1px solid #e0e0e0; border-radius:12px; padding:20px;'>"
            "<p style='font-size:11px; color:#888; margin:0 0 12px 0; letter-spacing:0.08em; text-transform:uppercase;'>Plan Changes</p>"
        )
        for row in changes:
            html += (
                "<div style='display:flex; justify-content:space-between; padding:8px 10px; "
                "background:#f7f7f5; border-radius:6px; margin-bottom:6px;'>"
                f"<span style='font-size:13px; color:#1a1a1a;'>{escape(row['date'])} — {escape(row['session_name'])}</span>"
                f"<span style='font-size:12px; color:#666;'>{escape(row.get('details', ''))[:60]}</span>"
                "</div>"
            )
        html += "</div>"
    else:
        html += (
            "<div style='background:#f7f7f5; border-radius:12px; padding:16px; text-align:center;'>"
            "<p style='font-size:13px; color:#888; margin:0;'>No changes made to next week's plan.</p>"
            "</div>"
        )

    html += "</div>"

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
    week_start = today - timedelta(days=today.weekday() + 1)  # last Monday
    week_end = today
    next_week_start = today + timedelta(days=1)
    next_week_end = today + timedelta(days=7)

    this_week = get_week_plan(all_rows, week_start, week_end)
    next_week = get_week_plan(all_rows, next_week_start, next_week_end)

    if not next_week:
        print("No next week plan found. Exiting.")
        return

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
        git_commit_and_push(f"Weekly review update {today.isoformat()}")
    else:
        print("No plan changes.")

    # Email
    send_review_email(summary, updated_rows)


if __name__ == "__main__":
    main()