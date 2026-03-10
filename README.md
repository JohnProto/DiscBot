# 📈 Discord Wordle Analytics Bot

A highly robust, enterprise-grade Discord bot designed to track, analyze, and visualize your server's daily Wordle performance. 

Moving beyond simple win/loss ratios, this bot introduces advanced sports sabermetrics—specifically **WAR (Wordle Above Replacement)**—to mathematically determine who is carrying the group chat and who is dragging the server average down.

## ✨ Key Features
* **Advanced Sabermetrics (WAR):** Dynamically calculates daily server averages to reward players who score well on difficult days and punish players who struggle on easy days.
* **Smart Name Parsing:** Flawlessly attributes scores whether a player is directly pinged by the official Wordle bot, mentioned via plain text, or using emojis in their display name.
* **Chronological Data Tracking:** Built-in caching system that correctly aligns player history, automatically handling missing days and late-joiners.
* **Data Visualization:** Generates beautiful, high-resolution `matplotlib` graphs directly in Discord for both individual performance and head-to-head comparisons.
* **Automated Daily Recaps:** Listens for the Official Wordle Bot's daily recap and automatically replies with the updated server leaderboard.

---

## 💻 Commands

### Public Slash Commands
| Command | Description |
| :--- | :--- |
| `/wordlestats` | Displays the current Season Leaderboard (Rank, Name, Average, Win %, WAR, Games Played). |
| `/genplots [player]` | Generates a detailed WAR history graph for a specific player. |
| `/compare [players]` | Generates a chronological multi-line graph comparing up to 5 players. Select **🌟 ALL PLAYERS 🌟** to graph the entire server. Features gray dotted lines to visually expose missed (AFK) days. |

### Admin/Owner Commands
| Command | Description |
| :--- | :--- |
| `/rescan` | Wipes the current database and performs a full historical scan of the channel to rebuild the cache from scratch. Safely handles Discord API rate limits. |
| `!sync` | (Message Command) Syncs all slash commands to the current Discord server. Restricted to the Bot Owner. |

---

## 🧮 The Math: Wordle Above Replacement (WAR)
Why use WAR? Because getting a 4/6 on a hard puzzle is impressive, but getting a 4/6 on an easy puzzle is barely average.

1. **Daily Average:** The bot calculates the mean score of all players for a specific day. *(Note: X/6 failures are calculated as a 7).*
2. **Player Differential:** The bot subtracts the player's score from the daily average.
3. **Cumulative Score:** If the daily average is 4.5 and you score a 3, you earn **+1.5 WAR**. If you score a 6, you earn **-1.5 WAR**. These scores are tallied over the season.

* **Positive WAR (+):** The player consistently outperforms the group.
* **Negative WAR (-):** The player is mathematically lowering the group average.

---

## 🚀 Future Work & Roadmap
* **Weekly/Monthly Awards:** Automated Friday recaps highlighting the "Player of the Week," "Biggest Choke," and "Most Improved."
* **Head-to-Head Win/Loss Records:** A command to see direct matchup stats between two players (e.g., "Max has beaten Ioannis 45 times, Ioannis has beaten Max 12 times").
* **Web Dashboard Integration:** Exporting the `wordle_cache.json` data to a lightweight Next.js or React web dashboard for interactive, browser-based chart hovering and deeper analytics.

---

## 🛠️ Setup & Installation
1. Clone the repository.
2. Install requirements: `pip install discord.py matplotlib numpy`
3. Edit `config.json` with your Official Wordle Bot ID, desired Fail Penalty (default: 7), and Season Start Date.
4. Run the bot: `python bot.py`
5. In your Discord server, type `!sync` to register the slash commands, then run `/rescan` to build your initial database!