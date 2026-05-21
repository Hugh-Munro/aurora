import os
import time
import csv
from datetime import datetime, timedelta
from urllib.parse import urlencode
import requests
from dotenv import load_dotenv
from google import genai

load_dotenv()

# Paths
STRAVA_TOKEN_FILE = "strava_tokens.json"
TRAINING_LOG_PATH = r"C:\Users\hugom\OneDrive\Desktop\Root\Personal\Fitness\training\training_log.csv"
TARGETS_PATH = r"C:\Users\hugom\OneDrive\Desktop\Root\Personal\Fitness\training\training_targets.csv"

CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Strava ---

def load_tokens():
    import json
    # GitHub Actions: use environment variable
    refresh_token = os.getenv("STRAVA_REFRESH_TOKEN")
    if refresh_token:
        return {
            "access_token": None,
            "refresh_token": refresh_token,
            "expires_at": 0,  # force refresh
        }
    # Local: use token file
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
        # Only save to file when running locally
        if not os.getenv("STRAVA_REFRESH_TOKEN"):
            with open(STRAVA_TOKEN_FILE, "w") as f:
                json.dump(tokens, f)
    return tokens

def get_strava_activities(access_token, days=7):
    after = int((datetime.now() - timedelta(days=days)).timestamp())
    response = requests.get(
        "https://www.strava.com/api/v3/athlete/activities",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"after": after, "per_page": 50},
    )
    activities = response.json()
    rows = []
    for a in activities:
        rows.append({
            "date": a["start_date_local"][:10],
            "type": a["type"],
            "distance_km": round(a["distance"] / 1000, 2),
            "duration_min": round(a["moving_time"] / 60, 1),
            "avg_heart_rate": a.get("average_heartrate", "N/A"),
        })
    return rows

# --- Read CSVs ---

def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def filter_last_7_days(log_rows):
    cutoff = datetime.now() - timedelta(days=7)
    filtered = []
    for row in log_rows:
        try:
            row_date = datetime.strptime(row["date"], "%Y-%m-%d")
            if row_date >= cutoff:
                filtered.append(row)
        except ValueError:
            continue
    return filtered

# --- Build prompt ---

def build_prompt(strava_activities, log_rows, targets):
    target = targets[0] if targets else {}

    strava_text = "STRAVA ACTIVITIES (last 7 days):\n"
    if strava_activities:
        for a in strava_activities:
            strava_text += f"  {a['date']} | {a['type']} | {a['distance_km']}km | {a['duration_min']}min | HR: {a['avg_heart_rate']}\n"
    else:
        strava_text += "  No activities recorded.\n"

    log_text = "TRAINING LOG (last 7 days):\n"
    if log_rows:
        for row in log_rows:
            log_text += (
                f"  {row['date']} | Location: {row['location']} | "
                f"Run: {row['run_km']}km RPE {row['run_rpe']} ({row['run_session_type']}) | "
                f"Gym: {row['gym_session']} | Notes: {row['notes']}\n"
            )
    else:
        log_text += "  No log entries for this period.\n"

    targets_text = f"""
WEEKLY TARGETS:
  Total run: {target.get('weekly_run_km_min', '?')}–{target.get('weekly_run_km_max', '?')} km
  Long run minimum: {target.get('long_run_min_km', '?')} km
  Quality sessions: {target.get('quality_sessions_per_week', '?')} per week
  Gym sessions (when in Dublin): {target.get('gym_sessions', '?')}
"""

    prompt = f"""
You are a running and fitness coach. Review the athlete's last 7 days of training data and provide concise, practical feedback.

{strava_text}
{log_text}
{targets_text}

CONTEXT: The athlete is based between Dublin and Waterford during summer, with gym access only in Dublin. The schedule is flexible — target-based rather than rigid.

Please provide:
1. A brief summary of the week (3–4 sentences max)
2. Whether weekly targets were hit (simple yes/no per target)
3. 3–5 bullet point recommendations for the coming week
4. Any concerns or patterns worth noting

Keep the tone direct and practical. No waffle.
"""
    return prompt

# --- Main ---

def main():
    print("Fetching Strava data...")
    tokens = load_tokens()
    tokens = refresh_if_needed(tokens)
    strava_activities = get_strava_activities(tokens["access_token"], days=7)

    print("Reading training log and targets...")
    log_rows = read_csv(TRAINING_LOG_PATH)
    targets = read_csv(TARGETS_PATH)
    recent_log = filter_last_7_days(log_rows)

    print("Sending to Gemini...\n")
    prompt = build_prompt(strava_activities, recent_log, targets)

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    print("=" * 60)
    print("WEEKLY TRAINING SUMMARY")
    print("=" * 60)
    print(response.text)

if __name__ == "__main__":
    main()