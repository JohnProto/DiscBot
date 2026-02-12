import discord
from discord import app_commands
from discord.ext import commands
import re
from collections import defaultdict
from datetime import datetime, timezone
import os
import json
import unicodedata
import io

# --- GRAPHING LIBRARIES ---
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# --- CONFIGURATION ---
WORDLE_BOT_ID = 1211781489931452447
TOKEN_FILE = 'token.txt'
FAIL_PENALTY = 7
STREAK_START_DATE = datetime(2025, 9, 6, tzinfo=timezone.utc)
CACHE_FILE = "wordle_cache.json"

# --- BOT SETUP ---
class WordleBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        print("Bot is starting...")

bot = WordleBot()

# --- UTILITIES ---
def read_token():
    token = os.getenv("DISCORD_TOKEN")
    if token:
        print("✅ Found token in Environment Variables.")
        return token.strip()
    try:
        with open(TOKEN_FILE, 'r') as f: return f.read().strip()
    except FileNotFoundError:
        print(f"Error: {TOKEN_FILE} not found."); exit()

def clean_name_for_table(name):
    name = unicodedata.normalize('NFKD', name)
    return "".join(c for c in name if c.isalnum() or c in " -_.,")

# --- CACHE & DATA ---
def load_cache():
    if not os.path.exists(CACHE_FILE): return {"last_message_id": None, "games": []}
    try: 
        with open(CACHE_FILE, 'r') as f: return json.load(f)
    except: return {"last_message_id": None, "games": []}

def save_cache(data):
    with open(CACHE_FILE, 'w') as f: json.dump(data, f, indent=4)

def get_name_map(guild):
    name_map = {}
    for member in guild.members:
        name_map[member.display_name.strip()] = str(member.id)
        name_map[member.name.strip()] = str(member.id)
    return name_map

def parse_message_text(content, name_map, fail_penalty):
    score_pattern = re.compile(r"([X\d])/6:(.*)")
    mention_pattern = re.compile(r"<@!?(\d+)>")
    results = []
    if "Your group is on a" in content:
        for line in content.split('\n'):
            line = line.strip()
            match = score_pattern.search(line)
            if match:
                raw_score = match.group(1)
                user_part = match.group(2)
                score = fail_penalty if raw_score == 'X' else int(raw_score)
                found_users = set()
                mentions = mention_pattern.findall(user_part)
                for uid in mentions: 
                    found_users.add(uid)
                    user_part = user_part.replace(f"<@{uid}>", "").replace(f"<@!{uid}>", "")
                for chunk in user_part.split('@'):
                    clean = chunk.strip()
                    if clean in name_map: found_users.add(name_map[clean])
                for uid in found_users: results.append((uid, score))
    return results

# UPDATED: Accepts channel/guild instead of interaction
async def update_data(channel, guild, full_rescan=False):
    cache = load_cache()
    name_map = get_name_map(guild)
    
    if full_rescan or cache["last_message_id"] is None:
        print("Performing FULL scan...")
        iterator = channel.history(limit=None, oldest_first=True)
        cache["games"] = []
    else:
        try:
            last_msg_obj = discord.Object(id=cache["last_message_id"])
            iterator = channel.history(limit=None, after=last_msg_obj, oldest_first=True)
        except:
             # Fallback if message deleted
            iterator = channel.history(limit=None, oldest_first=True)

    new_games_count = 0
    async for message in iterator:
        if message.created_at < STREAK_START_DATE: continue
        daily_results = parse_message_text(message.content, name_map, FAIL_PENALTY)
        if daily_results:
            game_entry = {'id': message.id, 'date': message.created_at.timestamp(), 'scores': {uid: score for uid, score in daily_results}}
            cache["games"].append(game_entry)
            new_games_count += 1
        cache["last_message_id"] = message.id
    
    if new_games_count > 0: save_cache(cache)
    return cache["games"]

# NEW HELPER: Generates the leaderboard string
def generate_leaderboard_text(guild, games_data):
    player_scores = defaultdict(list)
    player_war = defaultdict(float)
    
    for game in games_data:
        scores_map = game['scores']
        scores_list = list(scores_map.values())
        if not scores_list: continue
        day_avg = sum(scores_list) / len(scores_list)
        for uid, score in scores_map.items():
            player_scores[uid].append(score)
            player_war[uid] += (day_avg - score)

    leaderboard = []
    for uid, scores in player_scores.items():
        if len(scores) < 5: continue
        weighted_avg = sum(scores) / len(scores)
        wins = len([s for s in scores if s < FAIL_PENALTY])
        win_rate = (wins / len(scores)) * 100
        user = guild.get_member(int(uid))
        real_name = user.display_name if user else f"ID: {uid}"
        table_name = clean_name_for_table(real_name)
        
        leaderboard.append({
            'name': table_name, 'full_name': real_name,
            'avg': weighted_avg, 'win_rate': win_rate,
            'war': player_war[uid], 'games': len(scores)
        })

    leaderboard.sort(key=lambda x: x['war'], reverse=True)

    header = f"{'RK':<3} {'NAME':<14} {'AVG':<5} {'WIN%':<5} {'WAR':<6} {'GAMES'}"
    table_lines = [header, "=" * len(header)]
    for i, p in enumerate(leaderboard, 1):
        name_display = (p['name'][:12] + '..') if len(p['name']) > 12 else p['name']
        line = f"#{i:<2} {name_display:<14} {p['avg']:.2f}  {p['win_rate']:.0f}%   {p['war']:+.1f}   {p['games']}"
        table_lines.append(line)

    return (f"**📊 OFFICIAL WORDLE ANALYTICS**\n"
            f"*Season 1 Data ({len(games_data)} days scanned)*\n\n"
            f"```text\n" + "\n".join(table_lines) + "\n```\n"
            f"👑 **MVP:** {leaderboard[0]['full_name']}\n"
            f"💀 **LVP:** {leaderboard[-1]['full_name']}")

# --- AUTOCOMPLETE FUNCTION ---
async def player_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    cache = load_cache()
    unique_ids = set()
    for game in cache.get("games", []):
        for uid in game.get("scores", {}).keys():
            unique_ids.add(uid)
    choices = []
    for uid in unique_ids:
        member = interaction.guild.get_member(int(uid))
        display_name = member.display_name if member else f"Unknown ({uid})"
        if current.lower() in display_name.lower():
            choices.append(app_commands.Choice(name=display_name, value=uid))
    return choices[:25]

# --- SLASH COMMANDS ---

@bot.tree.command(name="genplots", description="Generate a WAR graph for a specific player")
@app_commands.autocomplete(player_id=player_autocomplete)
@app_commands.describe(player_id="Start typing a name to choose a player")
async def genplots(interaction: discord.Interaction, player_id: str):
    await interaction.response.defer(thinking=True)
    
    # Updated call with channel/guild
    games_data = await update_data(interaction.channel, interaction.guild)
    
    dates = []
    war_history = []
    current_war = 0.0
    games_played = 0
    
    games_data.sort(key=lambda x: x['date'])
    
    found_player = False
    for game in games_data:
        scores_map = game['scores']
        scores_list = list(scores_map.values())
        if not scores_list: continue
        day_avg = sum(scores_list) / len(scores_list)
        if player_id in scores_map:
            found_player = True
            player_score = scores_map[player_id]
            war_gained = day_avg - player_score
            games_played += 1
            current_war += war_gained
            dates.append(games_played)
            war_history.append(current_war)
            
    if not found_player:
        await interaction.followup.send(f"❌ No data found for player ID: {player_id}")
        return

    if len(war_history) < 2:
        await interaction.followup.send(f"📉 Not enough games ({len(war_history)}) to generate a graph.")
        return

    user = interaction.guild.get_member(int(player_id))
    name = user.display_name if user else "Unknown Player"
    
    plt.style.use('bmh')
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(dates, war_history, color='#1f77b4', linewidth=2.5, label='Cumulative WAR')
    wars_arr = np.array(war_history)
    ax.fill_between(dates, war_history, 0, where=(wars_arr >= 0), color='green', alpha=0.15, interpolate=True)
    ax.fill_between(dates, war_history, 0, where=(wars_arr < 0), color='red', alpha=0.15, interpolate=True)
    ax.axhline(0, color='black', linewidth=1.5, alpha=0.5)
    ax.set_title(f"Contribution History (WAR): {name}", fontsize=14, fontweight='bold')
    ax.set_xlabel("Games Played")
    ax.set_ylabel("Total WAR (Wordle Above Replacement)")
    ax.grid(True, alpha=0.3)
    
    last_war = war_history[-1]
    stats_text = f"Current WAR: {last_war:+.2f}\nGames: {games_played}"
    ax.text(0.02, 0.95, stats_text, transform=ax.transAxes, 
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    
    file = discord.File(buf, filename=f"{clean_name_for_table(name)}_war.png")
    await interaction.followup.send(f"📈 **WAR Analysis for {name}**", file=file)

@bot.tree.command(name="wordlestats", description="Show the Official Season 1 Leaderboard")
async def wordlestats(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    # Updated call
    games_data = await update_data(interaction.channel, interaction.guild)
    msg = generate_leaderboard_text(interaction.guild, games_data)
    await interaction.followup.send(msg)

@bot.tree.command(name="rescan", description="Force re-download history")
async def rescan(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    await interaction.followup.send("♻️ Rescanning history...")
    await update_data(interaction.channel, interaction.guild, full_rescan=True)
    await interaction.channel.send("✅ Done.")

# --- EVENTS ---

@bot.event
async def on_message(message):
    # 1. Ignore our own bot (always)
    if message.author == bot.user:
        return

    # 2. Check if the message is from the OFFICIAL Wordle Bot
    # (Remove the 'int()' cast if your ID is a string, but IDs are usually ints)
    if message.author.id == WORDLE_BOT_ID:
        
        # 3. Check for the magic Streak phrase
        if "Your group is on a" in message.content and "day streak" in message.content:
            print(f"🔥 Streak message detected from Official Bot ({message.author.name})!")
            
            # Update data (Scan the message that was just sent)
            games_data = await update_data(message.channel, message.guild)
            
            # Generate the stats table
            msg = generate_leaderboard_text(message.guild, games_data)
            
            # Reply to the streak message
            await message.channel.send(msg)

    # CRITICAL: Allow other commands (like !sync) to still work
    await bot.process_commands(message)

# --- ADMIN COMMANDS ---

@bot.command()
@commands.guild_only()
@commands.is_owner()
async def sync(ctx):
    print("Syncing commands to this server...")
    bot.tree.copy_global_to(guild=ctx.guild)
    synced = await bot.tree.sync(guild=ctx.guild)
    await ctx.send(f"✅ **Synced {len(synced)} commands!**")

@bot.command()
@commands.guild_only()
@commands.is_owner()
async def clearglobal(ctx):
    bot.tree.clear_commands(guild=None)
    await bot.tree.sync()
    await ctx.send("🧹 **Global commands cleared.**")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

if __name__ == "__main__":
    token = read_token()
    bot.run(token)