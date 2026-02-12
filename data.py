import os
import json
import asyncio
import discord
from config import CONFIG
from utils import parse_wordle_message, get_smart_name_map

CACHE_FILE = "wordle_cache.json"
CACHE_LOCK = asyncio.Lock()

def get_empty_cache():
    return {"last_message_id": None, "games": [], "players": {}}

def _process_game_stats(cache, game):
    """Internal: Updates player stats based on a single game."""
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
    print("🔄 Rebuilding Player Stats...")
    cache["players"] = {}
    cache["games"].sort(key=lambda x: x['date'])
    for game in cache["games"]:
        _process_game_stats(cache, game)
    return cache

async def load_cache():
    """Thread-safe load."""
    if not os.path.exists(CACHE_FILE): return get_empty_cache()
    try:
        with open(CACHE_FILE, 'r') as f:
            data = json.load(f)
            if "players" not in data: # Migration
                data = _rebuild_stats(data)
                with open(CACHE_FILE, 'w') as f2: json.dump(data, f2)
            return data
    except: return get_empty_cache()

async def update_data(channel, guild, full_rescan=False):
    """Main function to scan channel and update JSON."""
    async with CACHE_LOCK:
        # We assume load_cache() logic is duplicated here for atomic safety 
        # or we read the file directly inside the lock.
        if os.path.exists(CACHE_FILE):
             with open(CACHE_FILE, 'r') as f: cache = json.load(f)
        else: cache = get_empty_cache()
            
        if "players" not in cache: cache = _rebuild_stats(cache)

        name_map = get_smart_name_map(guild)
        
        if full_rescan or cache["last_message_id"] is None:
            print("Performing FULL scan...")
            iterator = channel.history(limit=None, oldest_first=True)
            cache = get_empty_cache() # Reset
        else:
            try:
                last_obj = discord.Object(id=cache["last_message_id"])
                iterator = channel.history(limit=None, after=last_obj, oldest_first=True)
            except:
                iterator = channel.history(limit=None, oldest_first=True)

        new_games = []
        scan_id = cache["last_message_id"]

        async for msg in iterator:
            scan_id = msg.id
            if msg.created_at < CONFIG["STREAK_START_DATE"]: continue
            
            results = parse_wordle_message(msg.content, name_map, CONFIG["FAIL_PENALTY"])
            if results:
                new_games.append({
                    'id': msg.id,
                    'date': msg.created_at.timestamp(),
                    'scores': {uid: s for uid, s in results}
                })

        # Save if changed
        if new_games or scan_id != cache["last_message_id"]:
            if new_games:
                print(f"Found {len(new_games)} new games.")
                for game in new_games:
                    cache["games"].append(game)
                    _process_game_stats(cache, game)
            
            cache["last_message_id"] = scan_id
            with open(CACHE_FILE, 'w') as f: json.dump(cache, f, indent=4)
        
        return cache