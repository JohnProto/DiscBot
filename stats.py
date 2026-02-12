import discord
from discord import app_commands
from discord.ext import commands
import re
from collections import defaultdict
from datetime import datetime, timezone
import matplotlib.pyplot as plt
import os
import numpy as np
import json
import unicodedata

# --- CONFIGURATION ---
TOKEN_FILE = 'token.txt'
FAIL_PENALTY = 7
STREAK_START_DATE = datetime(2025, 9, 6, tzinfo=timezone.utc)
GRAPH_OUTPUT_FOLDER = "wordle_graphs"
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
    try:
        with open(TOKEN_FILE, 'r') as f: return f.read().strip()
    except FileNotFoundError:
        print(f"Error: {TOKEN_FILE} not found."); exit()

def clean_name_for_table(name):
    name = unicodedata.normalize('NFKD', name)
    return "".join(c for c in name if c.isalnum() or c in " -_.,")

# --- CACHE ---
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

async def update_data(interaction: discord.Interaction, full_rescan=False):
    cache = load_cache()
    name_map = get_name_map(interaction.guild)
    
    if full_rescan or cache["last_message_id"] is None:
        print("Performing FULL scan...")
        iterator = interaction.channel.history(limit=None, oldest_first=True)
        cache["games"] = []
    else:
        print("Performing INCREMENTAL scan...")
        last_msg_obj = discord.Object(id=cache["last_message_id"])
        iterator = interaction.channel.history(limit=None, after=last_msg_obj, oldest_first=True)

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

# --- ADMIN COMMANDS ---

@bot.command()
@commands.guild_only()
@commands.is_owner()
async def sync(ctx):
    """Syncs commands LOCALLY (Fast & Instant)"""
    # Debug Check
    cmds = bot.tree.get_commands()
    print(f"DEBUG: Found {len(cmds)} commands in memory.")
    
    if len(cmds) == 0:
        await ctx.send("⚠️ **Zero commands found!**\nYou probably ran `!clearglobal`. **Restart the bot** to reload the commands, then type `!sync` again.")
        return

    print("Syncing commands to this server...")
    bot.tree.copy_global_to(guild=ctx.guild)
    synced = await bot.tree.sync(guild=ctx.guild)
    await ctx.send(f"✅ **Synced {len(synced)} commands!**\n1. Refresh Discord (Ctrl+R)\n2. Type `/` to see them.")

@bot.command()
@commands.guild_only()
@commands.is_owner()
async def clearglobal(ctx):
    """Deletes GLOBAL commands to fix duplicates"""
    print("Clearing global commands...")
    bot.tree.clear_commands(guild=None)
    await bot.tree.sync()
    await ctx.send("🧹 **Global commands cleared.**\nNow **Restart the Bot** and type `!sync` to fix your menu.")

# --- APP COMMANDS ---

@bot.tree.command(name="wordlestats", description="Show the Official Season 1 Leaderboard")
async def wordlestats(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    games_data = await update_data(interaction)
    
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
        user = interaction.guild.get_member(int(uid))
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

    msg = (f"**📊 OFFICIAL WORDLE ANALYTICS**\n"
           f"*Season 1 Data ({len(games_data)} days scanned)*\n\n"
           f"```text\n" + "\n".join(table_lines) + "\n```\n"
           f"👑 **MVP:** {leaderboard[0]['full_name']}\n"
           f"💀 **LVP:** {leaderboard[-1]['full_name']}")
    await interaction.followup.send(msg)

@bot.tree.command(name="genplots", description="Generate performance graphs locally")
async def genplots(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    if not os.path.exists(GRAPH_OUTPUT_FOLDER): os.makedirs(GRAPH_OUTPUT_FOLDER)
    games_data = await update_data(interaction)
    if not games_data: await interaction.followup.send("No data found."); return

    games_data.sort(key=lambda x: x['date'])
    start_date = datetime.fromtimestamp(games_data[0]['date']).strftime('%b %Y')
    end_date = datetime.fromtimestamp(games_data[-1]['date']).strftime('%b %Y')
    
    player_data = defaultdict(lambda: {'games': [], 'avgs': [], 'war_history': [], 'current_war': 0.0, 'total_score': 0, 'game_count': 0})

    for game in games_data:
        scores_map = game['scores']
        scores_list = list(scores_map.values())
        if not scores_list: continue
        day_avg = sum(scores_list) / len(scores_list)
        for uid, score in scores_map.items():
            stats = player_data[uid]
            stats['total_score'] += score
            stats['game_count'] += 1
            stats['current_war'] += (day_avg - score)
            stats['games'].append(stats['game_count'])
            stats['avgs'].append(stats['total_score'] / stats['game_count'])
            stats['war_history'].append(stats['current_war'])

    plt.style.use('bmh')
    generated_count = 0
    for uid, stats in player_data.items():
        if stats['game_count'] < 5: continue
        user = interaction.guild.get_member(int(uid))
        name = user.display_name if user else f"User_{uid}"
        safe_name = "".join(x for x in name if x.isalnum() or x in " _-")
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 14))
        fig.suptitle(f"Wordle Analytics: {name}\n{start_date} - {end_date}", fontsize=18, fontweight='bold', y=0.96)
        
        ax1.plot(stats['games'], stats['avgs'], color='#2ca02c', linewidth=2.5)
        ax1.axhline(y=4.0, color='grey', linestyle='--', alpha=0.5)
        curr_avgs = stats['avgs']
        ax1.set_ylim(max(max(curr_avgs)+0.5, 6.0), min(min(curr_avgs)-0.2, 3.0))
        ax1.set_title("Performance Consistency (Lower is Better)")
        ax1.set_ylabel("Average Score")
        
        wars = stats['war_history']
        ax2.plot(stats['games'], wars, color='#1f77b4', linewidth=2)
        wars_arr = np.array(wars)
        ax2.fill_between(stats['games'], wars, 0, where=(wars_arr >= 0), color='green', alpha=0.15)
        ax2.fill_between(stats['games'], wars, 0, where=(wars_arr < 0), color='red', alpha=0.15)
        ax2.axhline(0, color='black', linewidth=1.5)
        ax2.set_title("Contribution to Group (WAR)")
        ax2.set_ylabel("Total WAR")
        ax2.set_xlabel("Games Played")
        
        plt.subplots_adjust(hspace=0.3, top=0.90, bottom=0.05)
        plt.savefig(f"{GRAPH_OUTPUT_FOLDER}/{safe_name}_stats.png", dpi=300, bbox_inches='tight')
        plt.close(fig)
        generated_count += 1

    await interaction.followup.send(f"✅ Generated {generated_count} graphs in `{GRAPH_OUTPUT_FOLDER}/`")

@bot.tree.command(name="rescan", description="Force re-download history")
async def rescan(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    await interaction.followup.send("♻️ Rescanning history...")
    await update_data(interaction, full_rescan=True)
    await interaction.channel.send("✅ Done.")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

if __name__ == "__main__":
    token = read_token()
    bot.run(token)