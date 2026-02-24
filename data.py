import os
import json
import asyncio
import logging
import time
import discord
from typing import Dict, List, Any, Optional
from config import CONFIG
from utils import parse_wordle_message, get_smart_name_map

logger = logging.getLogger("data")

CACHE_FILE = "wordle_cache.json"
CACHE_LOCK = asyncio.Lock()
CACHE_TTL = 60
_last_update_time = 0

def get_empty_cache() -> Dict[str, Any]:
    # Added current_streak to track the highest streak found
    return {"last_message_id": None, "games": [], "players": {}, "current_streak": 0}

async def _scan_discord_history(channel: discord.TextChannel, 
                              start_id: Optional[int], 
                              start_date: float, 
                              name_map: Dict[str, str]) -> List[Dict[str, Any]]:
    new_games = []
    
    if start_id:
        try:
            start_obj = discord.Object(id=start_id)
            iterator = channel.history(limit=None, after=start_obj, oldest_first=True)
        except:
            logger.warning("Invalid Message ID. Resetting scan to start date.")
            iterator = channel.history(limit=None, oldest_first=True, after=start_date)
    else:
        logger.info("Performing FULL scan.")
        iterator = channel.history(limit=None, oldest_first=True, after=start_date)

    processed = 0
    async for msg in iterator:
        processed += 1
        if processed % 500 == 0: logger.info(f"🔄 Scanning... {processed} messages.")

        if msg.created_at < start_date: continue
        if msg.author.id != CONFIG["WORDLE_BOT_ID"]: continue

        # Now unpacks BOTH results and the streak
        results, streak = parse_wordle_message(msg.content, name_map, CONFIG["FAIL_PENALTY"])
        if results:
            new_games.append({
                'id': msg.id,
                'date': msg.created_at.timestamp(),
                'scores': {uid: s for uid, s in results},
                'streak': streak  # <--- NEW
            })
            
    return new_games

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

async def update_data(channel: discord.TextChannel, guild: discord.Guild, full_rescan: bool = False) -> Dict[str, Any]:
    global _last_update_time
    
    async with CACHE_LOCK:
        if os.path.exists(CACHE_FILE):
             with open(CACHE_FILE, 'r') as f: cache = json.load(f)
        else: cache = get_empty_cache()
            
        if "players" not in cache: cache = _rebuild_stats(cache)
        if "current_streak" not in cache: cache["current_streak"] = 0

        now = time.time()
        if not full_rescan and (now - _last_update_time < CACHE_TTL):
            return cache

        name_map = get_smart_name_map(guild)
        last_id = None if full_rescan else cache["last_message_id"]
        
        new_games = await _scan_discord_history(channel, last_id, CONFIG["STREAK_START_DATE"], name_map)

        if new_games:
            logger.info(f"✅ Found {len(new_games)} new games.")
            for game in new_games:
                cache["games"].append(game)
                _process_game_stats(cache, game)
                
                # Keep track of the highest streak number seen
                if game.get("streak", 0) > cache.get("current_streak", 0):
                    cache["current_streak"] = game["streak"]
            
            if new_games:
                cache["last_message_id"] = new_games[-1]['id']
            
            with open(CACHE_FILE, 'w') as f: json.dump(cache, f, indent=4)
        
        _last_update_time = time.time()
        return cache