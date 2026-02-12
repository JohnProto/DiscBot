import discord
import logging
import traceback
from discord import app_commands
from discord.ext import commands
from config import get_token

# --- LOGGING CONFIGURATION ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("bot")

class WordleBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        logger.info("⚙️ Loading Cogs...")
        await self.load_extension("cogs")
        logger.info("✅ Bot setup complete!")

    async def on_ready(self):
        logger.info(f'🚀 Logged in as {self.user} (ID: {self.user.id})')
        logger.info('Ready!')

bot = WordleBot()

# --- GLOBAL ERROR HANDLER ---
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    # 1. Handle Cooldowns
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"⏳ Whoa there! Try again in {error.retry_after:.1f} seconds.", 
            ephemeral=True
        )
        return

    # 2. Handle Missing Permissions
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "❌ You don't have permission to use this command.", 
            ephemeral=True
        )
        return

    # 3. Handle Other/Unexpected Errors
    # Check if the error is actually just a wrapper around the real error
    original_error = getattr(error, 'original', error)
    
    # Log the full traceback to the console/file
    logger.error(f"❌ Unhandled Error in command '{interaction.command.name}': {original_error}")
    logger.error("".join(traceback.format_tb(original_error.__traceback__)))

    # Inform the user nicely (so they aren't left hanging)
    msg = "💥 An internal error occurred. The developer has been notified."
    
    if interaction.response.is_done():
        await interaction.followup.send(msg, ephemeral=True)
    else:
        await interaction.response.send_message(msg, ephemeral=True)

# Admin Sync Command
@bot.command()
@commands.is_owner()
async def sync(ctx):
    await bot.tree.sync(guild=ctx.guild)
    logger.info(f"Commands synced to guild: {ctx.guild.name}")
    await ctx.send("Synced!")

if __name__ == "__main__":
    bot.run(get_token())