import json
import os
import logging
from datetime import datetime, timezone, timedelta

# Create module-specific logger
logger = logging.getLogger("config")

CONFIG_FILE = "config.json"
TOKEN_FILE = "token.txt"

def load_config():
    defaults = {
        "wordle_bot_id": 0,
        "fail_penalty": 7,
        "streak_start_date": "2025-01-01",
        "timezone_offset": 0
    }
    
    if not os.path.exists(CONFIG_FILE):
        logger.warning(f"⚠️ {CONFIG_FILE} not found! Creating default...")
        with open(CONFIG_FILE, 'w') as f: json.dump(defaults, f, indent=4)
        raw = defaults
    else:
        try:
            with open(CONFIG_FILE, 'r') as f: raw = json.load(f)
        except Exception as e:
            logger.error(f"❌ Error loading config: {e}")
            raw = defaults

    try:
        date_str = raw.get("streak_start_date", "2025-01-01")
        start_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        logger.error("❌ Invalid date format. Using default.")
        start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)

    return {
        "WORDLE_BOT_ID": int(raw.get("wordle_bot_id", 0)),
        "FAIL_PENALTY": int(raw.get("fail_penalty", 7)),
        "STREAK_START_DATE": start_date,
        "SEASON_NAME": raw.get("season_name", "Season 1"), # <--- NEW
        "TZ": timezone(timedelta(hours=raw.get("timezone_offset", 0)))
    }

CONFIG = load_config()

def get_token():
    token = os.getenv("DISCORD_TOKEN")
    if token: 
        logger.info("✅ Found token in Environment Variables.")
        return token.strip()
    try:
        with open(TOKEN_FILE, 'r') as f: 
            logger.warning("⚠️ Reading token from local file (Not recommended for prod).")
            return f.read().strip()
    except FileNotFoundError:
        logger.critical("❌ Error: No token found (Env Var or File). Exiting.")
        exit()