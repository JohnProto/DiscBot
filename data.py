import os
import json
import asyncio
import logging
import time  # <--- NEW IMPORT
import discord
from config import CONFIG
from utils import parse_wordle_message, get_smart_name_map

# Module Logger
logger = logging.getLogger("data")

CACHE_FILE = "wordle_cache.json"
CACHE_LOCK = asyncio.Lock()

# DEBOUNCE CONFIGURATION
CACHE_TTL = 60  # Seconds to wait before checking Discord again
_last_update_time = 0  # Tracks when we last talked to Discord

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
    global _last_update_time
    
    async with CACHE_LOCK:
        # 1. Load Cache from Disk
        if os.path.exists(CACHE_FILE):
             with open(CACHE_FILE, 'r') as f: cache = json.load(f)
        else: cache = get_empty_cache()
            
        if "players" not in cache: cache = _rebuild_stats(cache)

        # 2. DEBOUNCE CHECK (The Optimization)
        # If not forcing a rescan, AND we updated recently... SKIP DISCORD.
        now = time.time()
        if not full_rescan and (now - _last_update_time < CACHE_TTL):
            # logger.info("⏳ Cache is fresh. Skipping Discord scan.")
            return cache

        # ---------------------------------------------------------
        # If we get here, we are actually going to scan Discord.
        # ---------------------------------------------------------

        name_map = get_smart_name_map(guild)
        
        if full_rescan or cache["last_message_id"] is None:
            logger.info(f"Performing FULL scan (Skipping messages before {CONFIG['STREAK_START_DATE']})...")
            iterator = channel.history(
                limit=None, 
                oldest_first=True, 
                after=CONFIG["STREAK_START_DATE"]
            )
            cache = get_empty_cache() 
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

        async for msg in iterator:
            processed_count += 1
            scan_id = msg.id
            
            if processed_count % 500 == 0:
                logger.info(f"🔄 Scanning... {processed_count} messages processed.")

            if msg.created_at < CONFIG["STREAK_START_DATE"]: continue
            if msg.author.id != CONFIG["WORDLE_BOT_ID"]: continue 

            results = parse_wordle_message(msg.content, name_map, CONFIG["FAIL_PENALTY"])
            if results:
                new_games.append({
                    'id': msg.id,
                    'date': msg.created_at.timestamp(),
                    'scores': {uid: s for uid, s in results}
                })

        # Save Results
        if new_games or scan_id != cache["last_message_id"]:
            if new_games:
                logger.info(f"✅ Scan Complete. Found {len(new_games)} new games.")
                for game in new_games:
                    cache["games"].append(game)
                    _process_game_stats(cache, game)
            else:
                logger.info("✅ Scan Complete. No new games.")
            
            cache["last_message_id"] = scan_id
            with open(CACHE_FILE, 'w') as f: json.dump(cache, f, indent=4)
        
        # Update the timestamp so we don't scan again for 60s
        _last_update_time = time.time()
        
        return cache