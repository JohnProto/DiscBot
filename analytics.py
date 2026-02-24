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