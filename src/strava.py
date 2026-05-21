import os
import time
import webbrowser
from datetime import datetime, timedelta
from urllib.parse import urlencode
import csv
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
STRAVA_TOKEN_FILE = "strava_tokens.json"
OUTPUT_PATH = "data/strava_activities.csv"

def get_tokens_via_browser():
    import json
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": "http://localhost",
        "response_type": "code",
        "scope": "activity:read_all",
    }
    url = "https://www.strava.com/oauth/authorize?" + urlencode(params)
    print("Opening Strava in your browser...")
    webbrowser.open(url)
    print("\nAfter authorising, copy the full URL from your browser and paste it here.")
    callback_url = input("Paste URL: ").strip()
    code = callback_url.split("code=")[1].split("&")[0]
    response = requests.post("https://www.strava.com/oauth/token", data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
    })
    tokens = response.json()
    with open(STRAVA_TOKEN_FILE, "w") as f:
        json.dump(tokens, f)
    print("Tokens saved.")
    return tokens

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

def get_activities(access_token, days=14):
    after = int((datetime.now() - timedelta(days=days)).timestamp())
    response = requests.get(
        "https://www.strava.com/api/v3/athlete/activities",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"after": after, "per_page": 50},
    )
    return response.json()

def format_pace(speed_ms):
    """Convert m/s to min/km string e.g. 5:30."""
    if not speed_ms or speed_ms == 0:
        return "N/A"
    seconds_per_km = 1000 / speed_ms
    mins = int(seconds_per_km // 60)
    secs = int(seconds_per_km % 60)
    return f"{mins}:{secs:02d}"

def format_duration(seconds):
    """Convert seconds to HH:MM:SS string."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def main():
    tokens = load_tokens()
    tokens = refresh_if_needed(tokens)
    activities = get_activities(tokens["access_token"])

    rows = []
    for a in activities:
        rows.append({
            "date": a["start_date_local"][:10],
            "type": a["type"],
            "distance_km": round(a["distance"] / 1000, 2),
            "duration": format_duration(a["moving_time"]),
            "avg_heart_rate": a.get("average_heartrate", "N/A"),
            "avg_pace_min_km": format_pace(a.get("average_speed", 0)),
        })

    # Print to terminal
    print(f"\nActivities in the last 14 days:\n")
    print(f"{'Date':<12} {'Type':<12} {'Dist (km)':<12} {'Duration':<12} {'Avg HR':<10} {'Avg Pace':<10}")
    print("-" * 68)
    for r in rows:
        print(f"{r['date']:<12} {r['type']:<12} {str(r['distance_km']):<12} {r['duration']:<12} {str(r['avg_heart_rate']):<10} {r['avg_pace_min_km']:<10}")

    # Save to CSV
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSaved to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()