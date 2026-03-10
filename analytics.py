import discord
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from typing import List, Dict, Any
from config import CONFIG
from utils import clean_name

def get_leaderboard_stats(guild: discord.Guild, cache: Dict[str, Any]) -> List[Dict[str, Any]]:
    stats_list = []
    
    for uid, stats in cache["players"].items():
        if stats["games_played"] < CONFIG["MIN_GAMES"]: continue
        
        avg = stats["total_score"] / stats["games_played"]
        win_rate = (stats["wins"] / stats["games_played"]) * 100
        
        user = guild.get_member(int(uid))
        real_name = user.display_name if user else f"ID: {uid}"
        
        stats_list.append({
            'name': clean_name(real_name),
            'full_name': real_name,
            'avg': avg,
            'win_rate': win_rate,
            'war': stats["total_war"],
            'games': stats["games_played"]
        })

    stats_list.sort(key=lambda x: x['war'], reverse=True)
    return stats_list

# Notice we now pass the whole cache instead of just an integer
def render_leaderboard_table(stats_list: List[Dict[str, Any]], cache: Dict[str, Any]) -> str:
    if not stats_list:
        return (f"**📊 OFFICIAL WORDLE ANALYTICS**\n"
                f"*{CONFIG['SEASON_NAME']} Data*\n\n"
                f"⚠️ **Not enough data yet.**\n"
                f"Players need at least {CONFIG['MIN_GAMES']} games to qualify.")

    # Get the streak out of the cache!
    streak_number = cache.get("current_streak", len(cache["games"]))

    header = f"{'RK':<3} {'NAME':<14} {'AVG':<5} {'WIN%':<5} {'WAR':<6} {'GAMES'}"
    table_lines = [header, "=" * len(header)]
    
    for i, p in enumerate(stats_list, 1):
        name_display = (p['name'][:12] + '..') if len(p['name']) > 12 else p['name']
        line = f"#{i:<2} {name_display:<14} {p['avg']:.2f}  {p['win_rate']:.0f}%   {p['war']:+.1f}   {p['games']}"
        table_lines.append(line)

    return (f"**📊 OFFICIAL WORDLE ANALYTICS**\n"
            f"*{CONFIG['SEASON_NAME']} Data ({streak_number}-Day Streak)*\n\n"
            f"```text\n" + "\n".join(table_lines) + "\n```\n"
            f"👑 **MVP:** {stats_list[0]['full_name']}\n"
            f"💀 **LVP:** {stats_list[-1]['full_name']}")

def generate_war_graph(user_name: str, war_history: List[float]) -> discord.File:
    """
    Generates a beautiful matplotlib graph of a player's WAR history.
    """
    dates = list(range(1, len(war_history) + 1))
    
    plt.style.use('bmh')
    fig, ax = plt.subplots(figsize=(10, 6))
    
    ax.plot(dates, war_history, color='#1f77b4', linewidth=2.5, label='Cumulative WAR')
    
    wars_arr = np.array(war_history)
    ax.fill_between(dates, war_history, 0, where=(wars_arr >= 0), color='green', alpha=0.15, interpolate=True)
    ax.fill_between(dates, war_history, 0, where=(wars_arr < 0), color='red', alpha=0.15, interpolate=True)
    
    ax.axhline(0, color='black', linewidth=1.5, alpha=0.5)
    ax.set_title(f"Contribution History (WAR): {user_name}", fontsize=14, fontweight='bold')
    ax.set_xlabel("Games Played")
    ax.set_ylabel("Total WAR")
    ax.grid(True, alpha=0.3)
    
    last_war = war_history[-1]
    stats_text = f"Current WAR: {last_war:+.2f}\nGames: {len(war_history)}"
    ax.text(0.02, 0.95, stats_text, transform=ax.transAxes, 
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return discord.File(buf, filename=f"{clean_name(user_name)}_war.png")

def generate_comparison_graph(guild: discord.Guild, cache: Dict[str, Any], uids: List[str]) -> discord.File:
    """
    Generates a chronological multi-line graph comparing players.
    Uses gray dotted lines for missed days to expose AFK players.
    """
    # 1. Map out exactly what WAR each player had on each specific streak day
    player_timelines = {uid: {} for uid in uids}
    current_war = {uid: 0.0 for uid in uids}

    for game in cache['games']:
        streak = game.get('streak')
        if not streak: continue

        scores = list(game['scores'].values())
        if not scores: continue
        day_avg = sum(scores) / len(scores)

        for uid in uids:
            if uid in game['scores']:
                score = game['scores'][uid]
                current_war[uid] += (day_avg - score)
                player_timelines[uid][streak] = current_war[uid]

    # 2. Start Drawing
    plt.style.use('bmh')
    fig, ax = plt.subplots(figsize=(12, 7))
    colors = ['#1f77b4', '#d62728', '#2ca02c', '#ff7f0e', '#9467bd']
    
    all_streaks = sorted(list(set(g.get('streak') for g in cache['games'] if g.get('streak'))))
    max_overall_streak = all_streaks[-1] if all_streaks else 0

    for idx, uid in enumerate(uids):
        user = guild.get_member(int(uid))
        name = user.display_name if user else f"Player {uid}"
        color = colors[idx % len(colors)]

        timeline = player_timelines[uid]
        if not timeline: continue

        played_streaks = sorted(timeline.keys())
        wars = [timeline[s] for s in played_streaks]

        # Draw the actual dots where they played
        ax.plot(played_streaks, wars, marker='o', markersize=5, linestyle='', color=color)

        # Connect the dots with our logic
        for i in range(len(played_streaks) - 1):
            s1, s2 = played_streaks[i], played_streaks[i+1]
            w1, w2 = wars[i], wars[i+1]

            if s2 - s1 == 1:
                # Played consecutive days: Solid line
                ax.plot([s1, s2], [w1, w2], linestyle='-', color=color, linewidth=2.5)
            else:
                # Skipped days: Draw horizontal AFK flatline in gray
                ax.plot([s1, s2-1], [w1, w1], linestyle=':', color='gray', linewidth=2, alpha=0.6)
                # Draw the jump when they finally played again
                ax.plot([s2-1, s2], [w1, w2], linestyle='--', color=color, linewidth=2, alpha=0.8)

        # If they haven't played up to the CURRENT day, draw a final gray flatline
        last_played = played_streaks[-1]
        last_war = wars[-1]
        if last_played < max_overall_streak:
            ax.plot([last_played, max_overall_streak], [last_war, last_war], linestyle=':', color='gray', linewidth=2, alpha=0.6)

        # Add them to the legend with their final score
        ax.plot([], [], color=color, linewidth=3, label=f"{name} ({last_war:+.2f})")

    # Add the Server Average baseline (WAR = 0)
    ax.axhline(0, color='black', linewidth=1.5, alpha=0.8, linestyle='--')
    
    ax.set_title("Chronological Head-to-Head Comparison", fontsize=16, fontweight='bold')
    ax.set_xlabel("Official Streak Day")
    ax.set_ylabel("Total WAR")
    ax.legend(loc="upper left")
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return discord.File(buf, filename="head_to_head.png")