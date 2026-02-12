import discord
from discord import app_commands
from discord.ext import commands
from config import CONFIG
import data
import analytics
from utils import clean_name

class WordleCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def player_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        cache = await data.load_cache() # Read-only load
        choices = []
        for uid in cache.get("players", {}).keys():
            member = interaction.guild.get_member(int(uid))
            display = member.display_name if member else f"Unknown ({uid})"
            if current.lower() in display.lower():
                choices.append(app_commands.Choice(name=display, value=uid))
        return choices[:25]

    @app_commands.command(name="genplots", description="Generate WAR graph")
    @app_commands.autocomplete(player_id=player_autocomplete)
    async def genplots(self, interaction: discord.Interaction, player_id: str):
        await interaction.response.defer(thinking=True)
        cache = await data.update_data(interaction.channel, interaction.guild)
        
        if player_id not in cache["players"]:
            await interaction.followup.send("❌ No data for this player.")
            return

        war_hist = cache["players"][player_id]["war_history"]
        if len(war_hist) < 2:
            await interaction.followup.send("📉 Not enough games for a graph.")
            return

        user = interaction.guild.get_member(int(player_id))
        name = user.display_name if user else "Unknown"
        
        file = analytics.generate_war_graph(name, war_hist)
        await interaction.followup.send(f"📈 **WAR Analysis for {name}**", file=file)

    @app_commands.command(name="wordlestats", description="Show Leaderboard")
    async def wordlestats(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        cache = await data.update_data(interaction.channel, interaction.guild)
        msg = analytics.generate_leaderboard(interaction.guild, cache)
        await interaction.followup.send(msg)

    @app_commands.command(name="rescan", description="Force Rescan")
    async def rescan(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send("♻️ Rescanning...")
        await data.update_data(interaction.channel, interaction.guild, full_rescan=True)
        await interaction.channel.send("✅ Done.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user: return
        
        if message.author.id == CONFIG["WORDLE_BOT_ID"]:
            if "Your group is on a" in message.content and "day streak" in message.content:
                print("🔥 Official Streak Detected!")
                cache = await data.update_data(message.channel, message.guild)
                msg = analytics.generate_leaderboard(message.guild, cache)
                await message.channel.send(msg)

async def setup(bot):
    await bot.add_cog(WordleCommands(bot))