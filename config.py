import json
import os
from datetime import datetime, timezone, timedelta

CONFIG_FILE = "config.json"
TOKEN_FILE = "token.txt"

def load_config():
    defaults = {
        "wordle_bot_id": 0,
        "fail_penalty": 7,
        "streak_start_date": "2025-01-01",
        "timezone_offset": 0
    }
    
    # Create default if missing
    if not os.path.exists(CONFIG_FILE):
        print(f"⚠️ {CONFIG_FILE} not found! Creating default...")
        with open(CONFIG_FILE, 'w') as f: json.dump(defaults, f, indent=4)
        raw = defaults
    else:
        try:
            with open(CONFIG_FILE, 'r') as f: raw = json.load(f)
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            raw = defaults

    # Parse Date
    try:
        date_str = raw.get("streak_start_date", "2025-01-01")
        start_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        print("❌ Invalid date format. Using default.")
        start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)

    return {
        "WORDLE_BOT_ID": int(raw.get("wordle_bot_id", 0)),
        "FAIL_PENALTY": int(raw.get("fail_penalty", 7)),
        "STREAK_START_DATE": start_date,
        "TZ": timezone(timedelta(hours=raw.get("timezone_offset", 0)))
    }

# Load immediately on import
CONFIG = load_config()

def get_token():
    token = os.getenv("DISCORD_TOKEN")
    if token: return token.strip()
    try:
        with open(TOKEN_FILE, 'r') as f: return f.read().strip()
    except FileNotFoundError:
        print(f"❌ Error: {TOKEN_FILE} or DISCORD_TOKEN env var not found.")
        exit()