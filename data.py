import os
import json
import asyncio
import logging
import discord
from datetime import datetime
from config import CONFIG
from utils import parse_wordle_message, get_smart_name_map

# Module Logger
logger = logging.getLogger("data")

CACHE_FILE = "wordle_cache.json"
CACHE_LOCK = asyncio.Lock()

def get_empty_cache():
    return {"last_message_id": None, "games": [], "players": {}}

def _process_game_stats(cache, game):
    scores = list(game['scores'].values())
    if not scores: return
    day_avg = sum(scores) / len(scores)
    
    for uid, score in game['scores'].items():
        if uid not in cache["players"]:
            cache["players"][uid] = {
                "scores": [], "war_history": [], "total_war": 0.0,
                "total_score": 0, "wins": 0, "games_played": 0
            }
        
        p = cache["players"][uid]
        war_gained = day_avg - score
        p["scores"].append(score)
        p["war_history"].append(p["total_war"] + war_gained)
        p["total_war"] += war_gained
        p["total_score"] += score
        if score < CONFIG["FAIL_PENALTY"]: p["wins"] += 1
        p["games_played"] += 1

def _rebuild_stats(cache):
    logger.info("🔄 Rebuilding Player Stats Cache...")
    cache["players"] = {}
    cache["games"].sort(key=lambda x: x['date'])
    for game in cache["games"]:
        _process_game_stats(cache, game)
    return cache

async def load_cache():
    if not os.path.exists(CACHE_FILE): return get_empty_cache()
    try:
        with open(CACHE_FILE, 'r') as f:
            data = json.load(f)
            if "players" not in data: 
                logger.warning("⚠️ Old cache detected. Triggering migration.")
                data = _rebuild_stats(data)
                with open(CACHE_FILE, 'w') as f2: json.dump(data, f2)
            return data
    except Exception as e:
        logger.error(f"❌ Corrupt cache file: {e}")
        return get_empty_cache()

async def update_data(channel, guild, full_rescan=False):
    async with CACHE_LOCK:
        # Load Cache
        if os.path.exists(CACHE_FILE):
             with open(CACHE_FILE, 'r') as f: cache = json.load(f)
        else: cache = get_empty_cache()
            
        if "players" not in cache: cache = _rebuild_stats(cache)

        name_map = get_smart_name_map(guild)
        
        # DETERMINE START POINT
        if full_rescan or cache["last_message_id"] is None:
            logger.info(f"Performing FULL scan (Skipping messages before {CONFIG['STREAK_START_DATE']})...")
            
            # OPTIMIZATION: 
            # We tell Discord: "Don't even send me messages older than the Start Date."
            # This saves HUGE amounts of time/API calls.
            iterator = channel.history(
                limit=None, 
                oldest_first=True, 
                after=CONFIG["STREAK_START_DATE"]
            )
            cache = get_empty_cache() # Reset Data
        else:
            try:
                last_obj = discord.Object(id=cache["last_message_id"])
                iterator = channel.history(limit=None, after=last_obj, oldest_first=True)
            except:
                logger.warning("Last message ID invalid. Rescanning from start date.")
                iterator = channel.history(
                    limit=None, 
                    oldest_first=True, 
                    after=CONFIG["STREAK_START_DATE"]
                )

        new_games = []
        scan_id = cache["last_message_id"]
        processed_count = 0

        # SCAN LOOP
        async for msg in iterator:
            processed_count += 1
            scan_id = msg.id
            
            # Progress Log every 500 messages (Prevent "Is it dead?" panic)
            if processed_count % 500 == 0:
                logger.info(f"🔄 Scanning... {processed_count} messages processed so far.")

            # Safety check (Double check date even if API filtered)
            if msg.created_at < CONFIG["STREAK_START_DATE"]: continue
            
            results = parse_wordle_message(msg.content, name_map, CONFIG["FAIL_PENALTY"])
            if results:
                new_games.append({
                    'id': msg.id,
                    'date': msg.created_at.timestamp(),
                    'scores': {uid: s for uid, s in results}
                })

        # SAVE RESULTS
        if new_games or scan_id != cache["last_message_id"]:
            if new_games:
                logger.info(f"✅ Scan Complete. Found {len(new_games)} new games. Updating stats.")
                for game in new_games:
                    cache["games"].append(game)
                    _process_game_stats(cache, game)
            else:
                logger.info("✅ Scan Complete. No new Wordle games found.")
            
            cache["last_message_id"] = scan_id
            with open(CACHE_FILE, 'w') as f: json.dump(cache, f, indent=4)
        
        return cache