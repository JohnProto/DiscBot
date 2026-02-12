# 🟩 The Wordle Tribunal ⬛
### *Mathematically proving which of your friends is dragging the team down.*

**The Wordle Tribunal** is a Python Discord bot designed for one purpose: **Accountability.** It scrapes your group's Wordle chat history, parses the scores, and calculates advanced sabermetrics (like WAR) to determine who is carrying the streak and who is actively trying to kill it.

---

## 📊 Features

### 1. The "WAR" Stat (Wordle Above Replacement)
Standard averages are boring. This bot calculates **WAR**:
* **Positive WAR (+):** You beat the group average. You are a hero.
* **Negative WAR (-):** You scored worse than the average. You are an anchor.
* **Zero WAR:** You exist.

### 2. The Leaderboard (`/wordlestats`)
A generated ASCII table that ranks players by their contribution.
* **MVP:** The player with the highest total WAR (The Backpack).
* **LVP:** The player with the lowest total WAR (The Liability).
* **Hybrid Scanning:** Detects players via `@Mentions` AND plain text names (for when Discord fails to tag them).

### 3. Visual Shaming (`/genplots`)
Generates high-quality `matplotlib` graphs saved locally to your machine:
* **Consistency Graph:** Tracks your running average over time.
* **Contribution Graph:** A cumulative chart of your WAR. (Green area = Good, Red area = Bad).

### 4. Speed & Caching
* First run: Scans all history (slow).
* Next runs: **Instant**. Uses `wordle_cache.json` to only fetch new messages.

---

## 🛠️ Installation

### 1. Prerequisites
You need Python installed. Then, grab the libraries:
```bash
pip install discord.py matplotlib numpy
```

### 2. The Token
Create a file named `token.txt` in the same folder as the script. Paste your Discord Bot Token inside it (and nothing else).
```text
OTk5... (your token here)
```

### 3. Permissions
In the **Discord Developer Portal**:
1.  Go to **Bot** -> **Privileged Gateway Intents**.
2.  Enable **Message Content Intent** (Critical! The bot can't read scores without this).
3.  Enable **Server Members Intent** (To look up names).

---

## 🎮 Commands

### 🟢 Slash Commands (For everyone)
These are the modern, fancy commands that appear when you type `/`.

| Command | Description |
| :--- | :--- |
| **`/wordlestats`** | Displays the official Season 1 Leaderboard. |
| **`/genplots`** | Generates analytics graphs for every player in the `wordle_graphs/` folder. |
| **`/rescan`** | Forces a full re-download of chat history (use if data looks wrong). |

### 🔴 Admin Commands (Text-based)
These are "classic" commands used to manage the bot. Only the **Bot Owner** can use them.

| Command | Description |
| :--- | :--- |
| **`!sync`** | **CRITICAL.** Forces the Slash Commands to appear in your server. Run this if `/` shows nothing. |
| **`!clearglobal`** | Wipes global commands to fix "Duplicate Command" glitches. |

---

## 🚀 Quick Start Guide

1.  **Run the script:**
    ```bash
    python wordle_bot.py
    ```
2.  **Wait for the login message:**
    ```text
    Logged in as WordleBot#1234
    Bot is starting...
    ```
3.  **Go to your Discord Server.**
4.  Type **`!sync`** in the chat.
    * *Bot replies: "✅ Synced X commands!"*
5.  **Refresh Discord** (`Ctrl + R`).
6.  Type **`/wordlestats`** and watch the chaos unfold.

---

## 🧪 The "Science" (For Nerds)

**How WAR is calculated:**
Every day, the bot calculates the **Group Average** for that specific puzzle.
* If Group Avg is `4.5` and you get a `3`, you gain **+1.5 WAR**.
* If Group Avg is `4.5` and you get a `6`, you lose **-1.5 WAR**.
* If you fail (`X/6`), you are penalized with a score of **7**.

This ensures that getting a `3/6` on a hard day is worth more than getting a `3/6` on an easy day.

---

## 🐛 Troubleshooting

**"I don't see the slash commands!"**
1.  Did you run `!sync`?
2.  Did you restart your Discord app (`Ctrl+R`)?
3.  Does the bot have the `applications.commands` scope in the invite link?

**"The table looks misaligned!"**
The bot automatically strips emojis from names in the table view to keep columns straight. If it's still weird, tell your friends to stop using Zalgo text in their usernames.

**"It's seeing duplicate commands!"**
1.  Run `!clearglobal`.
2.  Restart the bot script.
3.  Run `!sync`.
4.  Restart Discord.

---

### *Disclaimer*
*This bot is not affiliated with The New York Times. It is, however, affiliated with ruining friendships over 5-letter words.*