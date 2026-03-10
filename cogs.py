import discord
import logging
from discord import app_commands
from discord.ext import commands
from config import CONFIG
import data
import analytics

logger = logging.getLogger("cogs")

class WordleCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def player_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        cache = await data.load_cache()
        choices = []
        for uid in cache.get("players", {}).keys():
            member = interaction.guild.get_member(int(uid))
            display = member.display_name if member else f"Unknown ({uid})"
            if current.lower() in display.lower():
                choices.append(app_commands.Choice(name=display, value=uid))
        return choices[:25]
    
    @app_commands.command(name="compare", description="[WIP] Compare multiple player graphs")
    @app_commands.autocomplete(player1=player_autocomplete, player2=player_autocomplete, player3=player_autocomplete, player4=player_autocomplete, player5=player_autocomplete)
    async def compare(self, interaction: discord.Interaction, 
                      player1: str = None, 
                      player2: str = None, 
                      player3: str = None, 
                      player4: str = None, 
                      player5: str = None,
                      compare_all: bool = False):
        
        await interaction.response.defer(thinking=True, ephemeral=True)
        
        # --- THE BIOMETRIC LOCK ---
        YOUR_DISCORD_ID = 1003788126508040334
        
        if interaction.user.id != YOUR_DISCORD_ID:
            logger.warning(f"Unauthorized access attempt to /compare by {interaction.user.name}")
            await interaction.followup.send("🚧 This command is currently in development.", ephemeral=True)
            return
            
        logger.info(f"Stealth command /compare used by {interaction.user.name}")
        cache = await data.update_data(interaction.channel, interaction.guild)
        
        uids_to_compare = []
        
        # Logic: If they chose "All", grab everyone who qualifies for the leaderboard
        if compare_all:
            for uid, stats in cache["players"].items():
                if stats["games_played"] >= CONFIG.get("MIN_GAMES", 5):
                    uids_to_compare.append(uid)
        else:
            # Logic: Collect whichever specific players they typed in
            inputs = [player1, player2, player3, player4, player5]
            for p in inputs:
                if p and p in cache["players"] and p not in uids_to_compare:
                    uids_to_compare.append(p)
                    
        # Sanity check
        if len(uids_to_compare) < 2:
            await interaction.followup.send("❌ Please select at least 2 valid players, or set `compare_all` to True.", ephemeral=True)
            return

        # Generate the graph
        file = analytics.generate_comparison_graph(interaction.guild, cache, uids_to_compare)
        await interaction.followup.send(f"🤫 **Confidential Comparison ({len(uids_to_compare)} Players)**", file=file, ephemeral=True)

    @app_commands.command(name="genplots", description="Generate WAR graph")
    @app_commands.autocomplete(player_id=player_autocomplete)
    async def genplots(self, interaction: discord.Interaction, player_id: str):
        # THE FIX: Added ephemeral=True so it hides the "thinking..." message
        await interaction.response.defer(thinking=True, ephemeral=True)
        
        logger.info(f"Command /genplots used by {interaction.user.name} (Hidden/Ephemeral)")
        
        cache = await data.update_data(interaction.channel, interaction.guild)
        
        if player_id not in cache["players"]:
            # THE FIX: Added ephemeral=True to error messages
            await interaction.followup.send("❌ No data for this player.", ephemeral=True)
            return

        war_hist = cache["players"][player_id]["war_history"]
        if len(war_hist) < 2:
            await interaction.followup.send("📉 Not enough games for a graph.", ephemeral=True)
            return

        user = interaction.guild.get_member(int(player_id))
        name = user.display_name if user else "Unknown"
        
        file = analytics.generate_war_graph(name, war_hist)
        
        # THE FIX: Added ephemeral=True to the final graph delivery
        await interaction.followup.send(f"📈 **WAR Analysis for {name}**", file=file, ephemeral=True)

    @app_commands.command(name="wordlestats", description="Show Leaderboard")
    async def wordlestats(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        logger.info(f"Command /wordlestats used by {interaction.user.name}")
        
        cache = await data.update_data(interaction.channel, interaction.guild)
        stats = analytics.get_leaderboard_stats(interaction.guild, cache)
        
        # FIX: Now we pass the full cache so it can read the streak number
        msg = analytics.render_leaderboard_table(stats, cache) 
        
        await interaction.followup.send(msg)

    @app_commands.command(name="rescan", description="Force Rescan")
    async def rescan(self, interaction: discord.Interaction):
        await interaction.response.defer()
        logger.warning(f"MANUAL RESCAN triggered by {interaction.user.name}")
        
        await interaction.followup.send("♻️ Rescanning history and wiping old data...")
        await data.update_data(interaction.channel, interaction.guild, full_rescan=True)
        await interaction.channel.send("✅ Done.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user: return
        
        if message.author.id == CONFIG["WORDLE_BOT_ID"]:
            if "Your group is on a" in message.content and "day streak" in message.content:
                logger.info(f"🔥 Official Streak Detected in {message.channel.name}! Replying with stats...")
                
                cache = await data.update_data(message.channel, message.guild)
                stats = analytics.get_leaderboard_stats(message.guild, cache)
                
                msg = analytics.render_leaderboard_table(stats, cache)
                
                # THE FIX: Changed message.channel.send to message.reply
                # mention_author=False means it links the messages but doesn't send a ping notification
                await message.reply(msg, mention_author=False)

async def setup(bot):
    await bot.add_cog(WordleCommands(bot))