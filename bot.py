import discord
import logging
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

# Admin Sync Command
@bot.command()
@commands.is_owner()
async def sync(ctx):
    await bot.tree.sync(guild=ctx.guild)
    logger.info(f"Commands synced to guild: {ctx.guild.name}")
    await ctx.send("Synced!")

if __name__ == "__main__":
    bot.run(get_token())