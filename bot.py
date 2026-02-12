import discord
from discord.ext import commands
from config import get_token

class WordleBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        print("⚙️ Loading Cogs...")
        await self.load_extension("cogs")
        print("✅ Bot is ready!")

    async def on_ready(self):
        print(f'Logged in as {self.user}')

bot = WordleBot()

# Admin Sync Command
@bot.command()
@commands.is_owner()
async def sync(ctx):
    await bot.tree.sync(guild=ctx.guild)
    await ctx.send("Synced!")

if __name__ == "__main__":
    bot.run(get_token())